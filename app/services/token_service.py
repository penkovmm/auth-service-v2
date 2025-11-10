"""
Token service for managing OAuth tokens.

Handles token encryption, decryption, storage, and retrieval.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_security_service
from app.core.logging import get_logger
from app.db.repositories.token import TokenRepository
from app.db.models import OAuthToken
from app.utils.exceptions import TokenError, TokenExpiredError, EncryptionError

logger = get_logger(__name__)


class TokenService:
    """Service for managing OAuth tokens."""

    def __init__(self, session: AsyncSession):
        """
        Initialize token service.

        Args:
            session: Async database session
        """
        self.session = session
        self.token_repo = TokenRepository(session)
        self.security = get_security_service()

    async def save_tokens(
        self,
        user_id: int,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_in: Optional[int] = None,
        token_type: str = "Bearer",
    ) -> OAuthToken:
        """
        Save OAuth tokens with encryption.

        Args:
            user_id: User ID
            access_token: Plain access token
            refresh_token: Plain refresh token (optional)
            expires_in: Token expiration time in seconds
            token_type: Token type (default: "Bearer")

        Returns:
            OAuthToken: Saved token record

        Raises:
            EncryptionError: If encryption fails
        """
        try:
            # Encrypt tokens
            encrypted_access = self.security.encrypt_token(access_token)
            encrypted_refresh = None
            if refresh_token:
                encrypted_refresh = self.security.encrypt_token(refresh_token)

            # Calculate expiration
            expires_at = None
            if expires_in:
                expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

            # Revoke existing active tokens for user
            await self.token_repo.revoke_all_user_tokens(user_id)

            # Save new token
            token = await self.token_repo.create_token(
                user_id=user_id,
                encrypted_access_token=encrypted_access,
                encrypted_refresh_token=encrypted_refresh,
                token_type=token_type,
                expires_at=expires_at,
            )

            logger.info(
                "tokens_saved",
                user_id=user_id,
                token_id=token.id,
                has_refresh_token=refresh_token is not None,
                expires_at=expires_at,
            )

            return token

        except Exception as e:
            logger.error(
                "token_save_failed",
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise EncryptionError(f"Failed to save tokens: {e}")

    async def get_access_token(self, user_id: int) -> str:
        """
        Get decrypted access token for user.

        Args:
            user_id: User ID

        Returns:
            str: Decrypted access token

        Raises:
            TokenError: If no active token found
            TokenExpiredError: If token is expired
            EncryptionError: If decryption fails
        """
        # Get active token
        token = await self.token_repo.get_active_token_by_user(user_id)

        if not token:
            logger.warning("no_active_token", user_id=user_id)
            raise TokenError(f"No active token found for user {user_id}")

        # Check expiration
        if token.expires_at and token.expires_at <= datetime.now(timezone.utc):
            logger.warning("token_expired", user_id=user_id, token_id=token.id)
            await self.token_repo.revoke_token(token.id)
            raise TokenExpiredError("Access token has expired")

        # Decrypt token
        try:
            decrypted_token = self.security.decrypt_token(token.encrypted_access_token)
            logger.debug("access_token_retrieved", user_id=user_id, token_id=token.id)
            return decrypted_token

        except Exception as e:
            logger.error(
                "token_decryption_failed",
                user_id=user_id,
                token_id=token.id,
                error=str(e),
            )
            raise EncryptionError(f"Failed to decrypt access token: {e}")

    async def get_tokens(self, user_id: int) -> Tuple[str, Optional[str]]:
        """
        Get decrypted access and refresh tokens for user.

        Args:
            user_id: User ID

        Returns:
            Tuple[str, Optional[str]]: (access_token, refresh_token)

        Raises:
            TokenError: If no active token found
            TokenExpiredError: If token is expired
            EncryptionError: If decryption fails
        """
        # Get active token
        token = await self.token_repo.get_active_token_by_user(user_id)

        if not token:
            logger.warning("no_active_token", user_id=user_id)
            raise TokenError(f"No active token found for user {user_id}")

        # Check expiration
        if token.expires_at and token.expires_at <= datetime.now(timezone.utc):
            logger.warning("token_expired", user_id=user_id, token_id=token.id)
            await self.token_repo.revoke_token(token.id)
            raise TokenExpiredError("Access token has expired")

        # Decrypt tokens
        try:
            access_token = self.security.decrypt_token(token.encrypted_access_token)
            refresh_token = None
            if token.encrypted_refresh_token:
                refresh_token = self.security.decrypt_token(
                    token.encrypted_refresh_token
                )

            logger.debug(
                "tokens_retrieved",
                user_id=user_id,
                token_id=token.id,
                has_refresh=refresh_token is not None,
            )

            return access_token, refresh_token

        except Exception as e:
            logger.error(
                "token_decryption_failed",
                user_id=user_id,
                token_id=token.id,
                error=str(e),
            )
            raise EncryptionError(f"Failed to decrypt tokens: {e}")

    async def refresh_tokens(
        self,
        user_id: int,
        new_access_token: str,
        new_refresh_token: Optional[str] = None,
        expires_in: Optional[int] = None,
    ) -> OAuthToken:
        """
        Refresh user tokens.

        Revokes old tokens and saves new ones.

        Args:
            user_id: User ID
            new_access_token: New access token
            new_refresh_token: New refresh token (optional)
            expires_in: Token expiration time in seconds

        Returns:
            OAuthToken: Updated token record
        """
        logger.info("tokens_refreshing", user_id=user_id)

        return await self.save_tokens(
            user_id=user_id,
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            expires_in=expires_in,
        )

    async def revoke_user_tokens(self, user_id: int) -> int:
        """
        Revoke all tokens for a user.

        Args:
            user_id: User ID

        Returns:
            int: Number of tokens revoked
        """
        count = await self.token_repo.revoke_all_user_tokens(user_id)
        logger.info("tokens_revoked", user_id=user_id, count=count)
        return count

    async def cleanup_expired_tokens(self) -> int:
        """
        Cleanup expired tokens.

        Revokes all expired tokens in the database.

        Returns:
            int: Number of tokens revoked
        """
        count = await self.token_repo.cleanup_expired_tokens()
        logger.info("expired_tokens_cleaned", count=count)
        return count
