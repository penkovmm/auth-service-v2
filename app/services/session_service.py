"""
Session service for managing user sessions.

Handles session creation, validation, and cleanup.
"""

import secrets
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.repositories.session import SessionRepository
from app.db.models import UserSession
from app.utils.exceptions import SessionError, SessionNotFoundError, SessionExpiredError

logger = get_logger(__name__)


class SessionService:
    """Service for managing user sessions."""

    def __init__(self, session: AsyncSession):
        """
        Initialize session service.

        Args:
            session: Async database session
        """
        self.session = session
        self.session_repo = SessionRepository(session)
        self.settings = get_settings()

    def _generate_session_id(self) -> str:
        """
        Generate secure session ID.

        Returns:
            str: Random session ID
        """
        return secrets.token_urlsafe(32)

    async def create_session(
        self,
        user_id: int,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> UserSession:
        """
        Create new user session.

        Args:
            user_id: User ID
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            UserSession: Created session

        Raises:
            SessionError: If session creation fails
        """
        try:
            # Generate session ID
            session_id = self._generate_session_id()

            # Calculate expiration
            expires_at = datetime.utcnow() + timedelta(
                hours=self.settings.session_expire_hours
            )

            # Create session
            user_session = await self.session_repo.create_session(
                session_id=session_id,
                user_id=user_id,
                expires_at=expires_at,
                ip_address=ip_address,
                user_agent=user_agent,
            )

            logger.info(
                "session_created",
                user_id=user_id,
                session_id=session_id,
                expires_at=expires_at,
                ip_address=ip_address,
            )

            return user_session

        except Exception as e:
            logger.error(
                "session_creation_failed",
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise SessionError(f"Failed to create session: {e}")

    async def get_session(self, session_id: str) -> UserSession:
        """
        Get session by ID.

        Args:
            session_id: Session ID

        Returns:
            UserSession: Session record

        Raises:
            SessionNotFoundError: If session not found
        """
        user_session = await self.session_repo.get_by_session_id(session_id)

        if not user_session:
            logger.warning("session_not_found", session_id=session_id)
            raise SessionNotFoundError(f"Session {session_id} not found")

        return user_session

    async def validate_session(self, session_id: str) -> UserSession:
        """
        Validate session.

        Checks if session exists, is active, and not expired.

        Args:
            session_id: Session ID

        Returns:
            UserSession: Valid session

        Raises:
            SessionNotFoundError: If session not found
            SessionExpiredError: If session is expired or inactive
        """
        user_session = await self.session_repo.get_active_session(session_id)

        if not user_session:
            logger.warning("session_validation_failed", session_id=session_id)
            raise SessionExpiredError("Session is invalid or expired")

        # Update last activity
        await self.session_repo.update_last_activity(session_id)

        logger.debug("session_validated", session_id=session_id, user_id=user_session.user_id)

        return user_session

    async def revoke_session(self, session_id: str) -> bool:
        """
        Revoke session.

        Args:
            session_id: Session ID

        Returns:
            bool: True if revoked, False if not found
        """
        revoked = await self.session_repo.revoke_session(session_id)

        if revoked:
            logger.info("session_revoked", session_id=session_id)
        else:
            logger.warning("session_revoke_failed_not_found", session_id=session_id)

        return revoked

    async def revoke_all_user_sessions(self, user_id: int) -> int:
        """
        Revoke all sessions for a user.

        Args:
            user_id: User ID

        Returns:
            int: Number of sessions revoked
        """
        count = await self.session_repo.revoke_all_user_sessions(user_id)
        logger.info("user_sessions_revoked", user_id=user_id, count=count)
        return count

    async def get_user_sessions(
        self, user_id: int, active_only: bool = True
    ) -> list[UserSession]:
        """
        Get all sessions for a user.

        Args:
            user_id: User ID
            active_only: If True, return only active sessions

        Returns:
            list[UserSession]: List of user sessions
        """
        sessions = await self.session_repo.get_user_sessions(user_id, active_only)
        logger.debug("user_sessions_retrieved", user_id=user_id, count=len(sessions))
        return sessions

    async def cleanup_expired_sessions(self) -> int:
        """
        Cleanup expired sessions.

        Revokes all expired sessions in the database.

        Returns:
            int: Number of sessions cleaned up
        """
        count = await self.session_repo.cleanup_expired_sessions()
        logger.info("expired_sessions_cleaned", count=count)
        return count

    async def extend_session(self, session_id: str) -> UserSession:
        """
        Extend session expiration.

        Args:
            session_id: Session ID

        Returns:
            UserSession: Updated session

        Raises:
            SessionNotFoundError: If session not found
        """
        user_session = await self.get_session(session_id)

        # Calculate new expiration
        new_expires_at = datetime.utcnow() + timedelta(
            hours=self.settings.session_expire_hours
        )

        # Update session
        updated_session = await self.session_repo.update(
            user_session.id,
            expires_at=new_expires_at,
            last_activity_at=datetime.utcnow(),
        )

        logger.info(
            "session_extended",
            session_id=session_id,
            new_expires_at=new_expires_at,
        )

        return updated_session
