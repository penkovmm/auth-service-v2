"""
HeadHunter OAuth service.

Handles OAuth 2.0 flow with HeadHunter API.
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urlencode
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.repositories.user import UserRepository, AllowedUserRepository
from app.db.repositories.session import OAuthStateRepository, OAuthExchangeCodeRepository
from app.db.models import User
from app.utils.exceptions import (
    OAuthError,
    OAuthStateError,
    OAuthCodeError,
    UserNotWhitelistedError,
    HeadHunterAPIError,
)

logger = get_logger(__name__)


class HeadHunterOAuthService:
    """Service for HeadHunter OAuth flow."""

    # HH API endpoints
    HH_AUTHORIZE_URL = "https://hh.ru/oauth/authorize"
    HH_TOKEN_URL = "https://hh.ru/oauth/token"
    HH_USER_INFO_URL = "https://api.hh.ru/me"

    def __init__(self, session: AsyncSession):
        """
        Initialize HH OAuth service.

        Args:
            session: Async database session
        """
        self.session = session
        self.user_repo = UserRepository(session)
        self.allowed_user_repo = AllowedUserRepository(session)
        self.state_repo = OAuthStateRepository(session)
        self.code_repo = OAuthExchangeCodeRepository(session)
        self.settings = get_settings()

    def _generate_state(self) -> str:
        """
        Generate secure random state for CSRF protection.

        Returns:
            str: Random state value
        """
        return secrets.token_urlsafe(32)

    async def get_authorization_url(
        self,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        Generate authorization URL for HH OAuth.

        Args:
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Tuple[str, str]: (authorization_url, state)
        """
        # Generate state
        state = self._generate_state()

        # Calculate state expiration
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=self.settings.oauth_state_expire_minutes
        )

        # Save state to database
        await self.state_repo.create_state(
            state=state,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Build authorization URL
        params = {
            "response_type": "code",
            "client_id": self.settings.hh_client_id,
            "state": state,
            "redirect_uri": self.settings.hh_redirect_uri,
        }

        authorization_url = f"{self.HH_AUTHORIZE_URL}?{urlencode(params)}"

        logger.info(
            "authorization_url_generated",
            state=state,
            redirect_uri=self.settings.hh_redirect_uri,
            ip_address=ip_address,
        )

        return authorization_url, state

    async def validate_state(self, state: str) -> bool:
        """
        Validate OAuth state.

        Args:
            state: State value to validate

        Returns:
            bool: True if valid

        Raises:
            OAuthStateError: If state is invalid or expired
        """
        state_obj = await self.state_repo.validate_and_mark_used(state)

        if not state_obj:
            logger.warning("state_validation_failed", state=state)
            raise OAuthStateError("Invalid or expired OAuth state")

        logger.debug("state_validated", state=state)
        return True

    async def exchange_code_for_token(
        self, code: str, state: str
    ) -> Dict[str, Any]:
        """
        Exchange authorization code for access token.

        Args:
            code: Authorization code from HH
            state: State value for validation

        Returns:
            Dict[str, Any]: Token response from HH API

        Raises:
            OAuthStateError: If state is invalid
            OAuthCodeError: If code exchange fails
            HeadHunterAPIError: If HH API returns error
        """
        # Validate state
        await self.validate_state(state)

        # Prepare token request
        token_data = {
            "grant_type": "authorization_code",
            "client_id": self.settings.hh_client_id,
            "client_secret": self.settings.hh_client_secret,
            "code": code,
            "redirect_uri": self.settings.hh_redirect_uri,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.HH_TOKEN_URL,
                    data=token_data,
                    headers={"User-Agent": self.settings.hh_user_agent},
                    timeout=30.0,
                )

                if response.status_code != 200:
                    error_data = response.json() if response.text else {}
                    logger.error(
                        "token_exchange_failed",
                        status_code=response.status_code,
                        error=error_data,
                    )
                    raise HeadHunterAPIError(
                        f"Token exchange failed: {error_data.get('error_description', 'Unknown error')}",
                        status_code=response.status_code,
                        response_data=error_data,
                    )

                token_response = response.json()

                logger.info(
                    "token_exchange_successful",
                    has_refresh_token="refresh_token" in token_response,
                    expires_in=token_response.get("expires_in"),
                )

                return token_response

        except httpx.HTTPError as e:
            logger.error("token_exchange_http_error", error=str(e))
            raise OAuthCodeError(f"HTTP error during token exchange: {e}")
        except Exception as e:
            logger.error("token_exchange_unexpected_error", error=str(e))
            raise OAuthCodeError(f"Unexpected error during token exchange: {e}")

    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """
        Get user information from HH API.

        Args:
            access_token: HH access token

        Returns:
            Dict[str, Any]: User info from HH API

        Raises:
            HeadHunterAPIError: If API request fails
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.HH_USER_INFO_URL,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "User-Agent": self.settings.hh_user_agent,
                    },
                    timeout=30.0,
                )

                if response.status_code != 200:
                    error_data = response.json() if response.text else {}
                    logger.error(
                        "user_info_request_failed",
                        status_code=response.status_code,
                        error=error_data,
                    )
                    raise HeadHunterAPIError(
                        f"Failed to fetch user info: {error_data.get('error_description', 'Unknown error')}",
                        status_code=response.status_code,
                        response_data=error_data,
                    )

                user_info = response.json()

                logger.info(
                    "user_info_retrieved",
                    hh_user_id=user_info.get("id"),
                    email=user_info.get("email"),
                )

                return user_info

        except httpx.HTTPError as e:
            logger.error("user_info_http_error", error=str(e))
            raise HeadHunterAPIError(f"HTTP error during user info request: {e}")
        except Exception as e:
            logger.error("user_info_unexpected_error", error=str(e))
            raise HeadHunterAPIError(f"Unexpected error during user info request: {e}")

    async def check_user_whitelist(self, hh_user_id: str) -> bool:
        """
        Check if user is in whitelist.

        Args:
            hh_user_id: HH user ID

        Returns:
            bool: True if user is allowed

        Raises:
            UserNotWhitelistedError: If user is not in whitelist
        """
        is_allowed = await self.allowed_user_repo.is_user_allowed(hh_user_id)

        if not is_allowed:
            logger.warning("user_not_whitelisted", hh_user_id=hh_user_id)
            raise UserNotWhitelistedError(
                f"User {hh_user_id} is not in the whitelist"
            )

        logger.debug("user_whitelist_check_passed", hh_user_id=hh_user_id)
        return True

    async def get_or_create_user(self, user_info: Dict[str, Any]) -> User:
        """
        Get existing user or create new one from HH user info.

        Args:
            user_info: User info from HH API

        Returns:
            User: User instance

        Raises:
            OAuthError: If user creation fails
        """
        hh_user_id = str(user_info.get("id"))

        # Check whitelist
        await self.check_user_whitelist(hh_user_id)

        # Try to get existing user
        user = await self.user_repo.get_by_hh_user_id(hh_user_id)

        if user:
            # Update user info
            updated_user = await self.user_repo.update_user_info(
                user_id=user.id,
                email=user_info.get("email"),
                first_name=user_info.get("first_name"),
                last_name=user_info.get("last_name"),
                middle_name=user_info.get("middle_name"),
            )

            # Update last login
            await self.user_repo.update_last_login(user.id)

            logger.info("user_updated", user_id=user.id, hh_user_id=hh_user_id)
            return updated_user

        # Create new user
        try:
            new_user = await self.user_repo.create_user(
                hh_user_id=hh_user_id,
                email=user_info.get("email"),
                first_name=user_info.get("first_name"),
                last_name=user_info.get("last_name"),
                middle_name=user_info.get("middle_name"),
            )

            logger.info("user_created", user_id=new_user.id, hh_user_id=hh_user_id)
            return new_user

        except Exception as e:
            logger.error(
                "user_creation_failed",
                hh_user_id=hh_user_id,
                error=str(e),
            )
            raise OAuthError(f"Failed to create user: {e}")

    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh access token using refresh token.

        Args:
            refresh_token: HH refresh token

        Returns:
            Dict[str, Any]: New token response

        Raises:
            HeadHunterAPIError: If refresh fails
        """
        token_data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.HH_TOKEN_URL,
                    data=token_data,
                    headers={"User-Agent": self.settings.hh_user_agent},
                    timeout=30.0,
                )

                if response.status_code != 200:
                    error_data = response.json() if response.text else {}
                    logger.error(
                        "token_refresh_failed",
                        status_code=response.status_code,
                        error=error_data,
                    )
                    raise HeadHunterAPIError(
                        f"Token refresh failed: {error_data.get('error_description', 'Unknown error')}",
                        status_code=response.status_code,
                        response_data=error_data,
                    )

                token_response = response.json()

                logger.info(
                    "token_refresh_successful",
                    has_refresh_token="refresh_token" in token_response,
                )

                return token_response

        except httpx.HTTPError as e:
            logger.error("token_refresh_http_error", error=str(e))
            raise HeadHunterAPIError(f"HTTP error during token refresh: {e}")
        except Exception as e:
            logger.error("token_refresh_unexpected_error", error=str(e))
            raise HeadHunterAPIError(f"Unexpected error during token refresh: {e}")
