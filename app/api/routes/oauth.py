"""
OAuth authentication routes.

Handles OAuth 2.0 flow with HeadHunter:
- /login - initiate OAuth flow
- /callback - OAuth callback handler
- /logout - logout user
"""

from fastapi import APIRouter, Depends, Request, HTTPException, status, Response, Cookie
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.database import get_db
from app.services import HeadHunterOAuthService, TokenService, SessionService
from app.db.repositories.audit import AuditLogRepository
from app.schemas import (
    OAuthURLResponse,
    LoginSuccessResponse,
    LogoutResponse,
    TokenResponse,
    GetTokenRequest,
)
from app.utils.exceptions import (
    OAuthError,
    OAuthStateError,
    UserNotWhitelistedError,
    SessionError,
)

logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["OAuth Authentication"])


def get_client_info(request: Request) -> tuple[str | None, str | None]:
    """
    Extract client IP and user agent from request.

    Args:
        request: FastAPI request

    Returns:
        tuple: (ip_address, user_agent)
    """
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return ip_address, user_agent


@router.get("/login", response_model=OAuthURLResponse)
async def login(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Initiate OAuth login flow.

    Returns HeadHunter authorization URL with state for CSRF protection.

    **Flow:**
    1. Generate random state for CSRF protection
    2. Save state to database with expiration
    3. Return authorization URL

    **Returns:**
    - authorization_url: URL to redirect user to HH authorization
    - state: CSRF protection token
    """
    ip_address, user_agent = get_client_info(request)

    oauth_service = HeadHunterOAuthService(db)

    try:
        authorization_url, state = await oauth_service.get_authorization_url(
            ip_address=ip_address,
            user_agent=user_agent,
        )

        logger.info(
            "login_initiated",
            ip_address=ip_address,
            state=state,
        )

        return OAuthURLResponse(
            authorization_url=authorization_url,
            state=state,
        )

    except Exception as e:
        logger.error(
            "login_initiation_failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate login: {str(e)}",
        )


@router.get("/callback")
async def oauth_callback(
    code: str,
    state: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    OAuth callback handler.

    Handles the redirect from HeadHunter after user authorization.

    **Flow:**
    1. Validate state (CSRF protection)
    2. Exchange code for access token
    3. Fetch user info from HH API
    4. Check user whitelist
    5. Create/update user in database
    6. Save encrypted tokens
    7. Create session
    8. Log audit event

    **Query Parameters:**
    - code: Authorization code from HH
    - state: CSRF protection token

    **Returns:**
    - message: Success message
    - session_id: Created session ID
    - user: User information

    **Errors:**
    - 400: Invalid state or code
    - 403: User not in whitelist
    - 500: Internal server error
    """
    ip_address, user_agent = get_client_info(request)

    oauth_service = HeadHunterOAuthService(db)
    token_service = TokenService(db)
    session_service = SessionService(db)
    audit_repo = AuditLogRepository(db)

    try:
        # Exchange code for token
        token_response = await oauth_service.exchange_code_for_token(code, state)

        access_token = token_response.get("access_token")
        refresh_token = token_response.get("refresh_token")
        expires_in = token_response.get("expires_in")

        # Get user info
        user_info = await oauth_service.get_user_info(access_token)

        # Get or create user (includes whitelist check)
        user = await oauth_service.get_or_create_user(user_info)

        # Save encrypted tokens
        await token_service.save_tokens(
            user_id=user.id,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
        )

        # Create session
        user_session = await session_service.create_session(
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Log successful login
        await audit_repo.log_login(
            user_id=user.id,
            hh_user_id=user.hh_user_id,
            session_id=user_session.session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            success=True,
        )

        await db.commit()

        logger.info(
            "login_successful",
            user_id=user.id,
            hh_user_id=user.hh_user_id,
            session_id=user_session.session_id,
        )

        # Create redirect response to parser.penkovmm.ru with session_id in query
        # We pass session_id via query parameter instead of cookie because cross-subdomain
        # cookies can be blocked by browsers due to SameSite policies
        redirect_url = f"https://parser.penkovmm.ru/auth/callback?session_id={user_session.session_id}"
        response = RedirectResponse(url=redirect_url, status_code=302)

        return response

    except OAuthStateError as e:
        logger.warning("oauth_state_error", error=str(e), state=state)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    except UserNotWhitelistedError as e:
        logger.warning("user_not_whitelisted", error=str(e), ip_address=ip_address)

        # Log failed login attempt
        await audit_repo.log_event(
            event_type="login",
            event_category="security",
            event_description="Login attempt by non-whitelisted user",
            success=False,
            ip_address=ip_address,
            user_agent=user_agent,
            error_message=str(e),
        )
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: User not authorized",
        )

    except OAuthError as e:
        logger.error("oauth_error", error=str(e), error_type=type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth error: {str(e)}",
        )

    except Exception as e:
        logger.error(
            "callback_failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication failed: {str(e)}",
        )


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    request: Request,
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Logout user.

    Revokes session and logs audit event.

    **Request Body:**
    - session_id: Session ID to revoke

    **Returns:**
    - message: Success message

    **Errors:**
    - 404: Session not found
    - 500: Internal server error
    """
    ip_address, user_agent = get_client_info(request)

    session_service = SessionService(db)
    audit_repo = AuditLogRepository(db)

    try:
        # Get session to retrieve user info
        user_session = await session_service.get_session(session_id)

        # Revoke session
        revoked = await session_service.revoke_session(session_id)

        if not revoked:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )

        # Log logout
        from app.db.repositories.user import UserRepository

        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(user_session.user_id)

        if user:
            await audit_repo.log_logout(
                user_id=user.id,
                hh_user_id=user.hh_user_id,
                session_id=session_id,
                ip_address=ip_address,
                user_agent=user_agent,
            )

        await db.commit()

        logger.info("logout_successful", session_id=session_id)

        return LogoutResponse()

    except HTTPException:
        raise

    except Exception as e:
        logger.error(
            "logout_failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Logout failed: {str(e)}",
        )


@router.post("/token", response_model=TokenResponse)
async def get_token(
    request_data: GetTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Get valid HH access token for a session.

    Retrieves current access token for the provided session.
    Automatically refreshes token if expired.

    **Request Body:**
    - session_id: Session ID from successful OAuth login

    **Returns:**
    - access_token: Valid HeadHunter API access token
    - expires_at: Token expiration timestamp
    - user_id: User ID

    **Errors:**
    - 401: Invalid session or session expired
    - 500: Internal server error
    """
    session_service = SessionService(db)
    token_service = TokenService(db)

    try:
        # Get and validate session
        user_session = await session_service.get_session(request_data.session_id)

        if not user_session or not user_session.is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired session",
            )

        # Get token (automatically refreshes if needed)
        access_token = await token_service.get_access_token(user_session.user_id)

        # Get full token object for expires_at
        token_obj = await token_service.token_repo.get_active_token_by_user(user_session.user_id)

        if not access_token or not token_obj:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to retrieve valid token. Please re-authenticate",
            )

        logger.info(
            "token_retrieved",
            user_id=user_session.user_id,
            session_id=request_data.session_id,
        )

        return TokenResponse(
            access_token=access_token,
            expires_at=token_obj.expires_at,
            user_id=user_session.user_id,
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(
            "token_retrieval_failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve token: {str(e)}",
        )


@router.get("/user_info")
async def get_user_info(
    session_id: str = Cookie(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Get user information for a session.

    Retrieves user information for the provided session.

    **Cookie:**
    - session_id: Session ID from successful OAuth login

    **Returns:**
    - user: User information (id, hh_user_id, email, first_name, last_name)

    **Errors:**
    - 401: Invalid session or session expired
    - 500: Internal server error
    """
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No session ID provided",
        )

    session_service = SessionService(db)

    try:
        # Get and validate session
        user_session = await session_service.get_session(session_id)

        if not user_session or not user_session.is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired session",
            )

        # Get user info
        from app.db.repositories.user import UserRepository
        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(user_session.user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        logger.info(
            "user_info_retrieved",
            user_id=user.id,
            session_id=session_id,
        )

        return {
            "user": {
                "id": user.id,
                "hh_user_id": user.hh_user_id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
            }
        }

    except HTTPException:
        raise

    except Exception as e:
        logger.error(
            "user_info_retrieval_failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve user info: {str(e)}",
        )
