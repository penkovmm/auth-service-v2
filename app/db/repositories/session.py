"""
Session repository for database operations.

Handles CRUD operations for UserSession, OAuthState, and OAuthExchangeCode models.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import UserSession, OAuthState, OAuthExchangeCode
from app.db.repositories.base import BaseRepository


class SessionRepository(BaseRepository[UserSession]):
    """Repository for UserSession model operations."""

    def __init__(self, session: AsyncSession):
        """Initialize session repository."""
        super().__init__(UserSession, session)

    async def get_by_session_id(self, session_id: str) -> Optional[UserSession]:
        """
        Get session by session ID.

        Args:
            session_id: Session ID

        Returns:
            UserSession instance or None if not found
        """
        return await self.get_by_field("session_id", session_id)

    async def get_active_session(self, session_id: str) -> Optional[UserSession]:
        """
        Get active session by session ID.

        Args:
            session_id: Session ID

        Returns:
            UserSession instance or None if not found or expired
        """
        stmt = select(UserSession).where(
            and_(
                UserSession.session_id == session_id,
                UserSession.is_active == True,
                UserSession.expires_at > datetime.now(timezone.utc),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_session(
        self,
        session_id: str,
        user_id: int,
        expires_at: datetime,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> UserSession:
        """
        Create new user session.

        Args:
            session_id: Unique session ID
            user_id: User ID
            expires_at: Session expiration time
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Created UserSession instance
        """
        return await self.create(
            session_id=session_id,
            user_id=user_id,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
            is_active=True,
        )

    async def update_last_activity(self, session_id: str) -> Optional[UserSession]:
        """
        Update session's last activity timestamp.

        Args:
            session_id: Session ID

        Returns:
            Updated UserSession instance or None if not found
        """
        session_obj = await self.get_by_session_id(session_id)
        if not session_obj:
            return None

        return await self.update(session_obj.id, last_activity_at=datetime.now(timezone.utc))

    async def revoke_session(self, session_id: str) -> bool:
        """
        Revoke session (set is_active=False).

        Args:
            session_id: Session ID

        Returns:
            True if revoked, False if not found
        """
        session_obj = await self.get_by_session_id(session_id)
        if not session_obj:
            return False

        await self.update(session_obj.id, is_active=False)
        return True

    async def revoke_all_user_sessions(self, user_id: int) -> int:
        """
        Revoke all sessions for a user.

        Args:
            user_id: User ID

        Returns:
            Number of sessions revoked
        """
        stmt = select(UserSession).where(
            and_(UserSession.user_id == user_id, UserSession.is_active == True)
        )
        result = await self.session.execute(stmt)
        sessions = result.scalars().all()

        count = 0
        for session_obj in sessions:
            await self.update(session_obj.id, is_active=False)
            count += 1

        return count

    async def get_user_sessions(
        self, user_id: int, active_only: bool = True
    ) -> List[UserSession]:
        """
        Get all sessions for a user.

        Args:
            user_id: User ID
            active_only: If True, return only active sessions

        Returns:
            List of UserSession instances
        """
        if active_only:
            stmt = select(UserSession).where(
                and_(
                    UserSession.user_id == user_id,
                    UserSession.is_active == True,
                    UserSession.expires_at > datetime.now(timezone.utc),
                )
            )
        else:
            stmt = select(UserSession).where(UserSession.user_id == user_id)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions (set is_active=False).

        Returns:
            Number of sessions cleaned up
        """
        stmt = select(UserSession).where(
            and_(
                UserSession.is_active == True, UserSession.expires_at <= datetime.now(timezone.utc)
            )
        )
        result = await self.session.execute(stmt)
        sessions = result.scalars().all()

        count = 0
        for session_obj in sessions:
            await self.update(session_obj.id, is_active=False)
            count += 1

        return count


class OAuthStateRepository(BaseRepository[OAuthState]):
    """Repository for OAuthState model operations."""

    def __init__(self, session: AsyncSession):
        """Initialize OAuth state repository."""
        super().__init__(OAuthState, session)

    async def get_by_state(self, state: str) -> Optional[OAuthState]:
        """
        Get OAuth state by state value.

        Args:
            state: State value

        Returns:
            OAuthState instance or None if not found
        """
        return await self.get_by_field("state", state)

    async def create_state(
        self,
        state: str,
        expires_at: datetime,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> OAuthState:
        """
        Create new OAuth state.

        Args:
            state: Unique state value
            expires_at: State expiration time
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Created OAuthState instance
        """
        return await self.create(
            state=state,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
            is_used=False,
        )

    async def validate_and_mark_used(self, state: str) -> Optional[OAuthState]:
        """
        Validate state and mark as used.

        Checks:
        - State exists
        - Not expired
        - Not already used

        Args:
            state: State value

        Returns:
            OAuthState instance if valid, None otherwise
        """
        stmt = select(OAuthState).where(
            and_(
                OAuthState.state == state,
                OAuthState.is_used == False,
                OAuthState.expires_at > datetime.now(timezone.utc),
            )
        )
        result = await self.session.execute(stmt)
        state_obj = result.scalar_one_or_none()

        if not state_obj:
            return None

        # Mark as used
        await self.update(state_obj.id, is_used=True, used_at=datetime.now(timezone.utc))
        await self.session.refresh(state_obj)

        return state_obj

    async def cleanup_expired_states(self) -> int:
        """
        Delete expired OAuth states.

        Returns:
            Number of states deleted
        """
        stmt = select(OAuthState).where(OAuthState.expires_at <= datetime.now(timezone.utc))
        result = await self.session.execute(stmt)
        states = result.scalars().all()

        count = 0
        for state_obj in states:
            await self.delete(state_obj.id)
            count += 1

        return count


class OAuthExchangeCodeRepository(BaseRepository[OAuthExchangeCode]):
    """Repository for OAuthExchangeCode model operations."""

    def __init__(self, session: AsyncSession):
        """Initialize OAuth exchange code repository."""
        super().__init__(OAuthExchangeCode, session)

    async def get_by_code(self, code: str) -> Optional[OAuthExchangeCode]:
        """
        Get exchange code by code value.

        Args:
            code: Authorization code

        Returns:
            OAuthExchangeCode instance or None if not found
        """
        return await self.get_by_field("code", code)

    async def create_exchange_code(
        self,
        code: str,
        state: str,
        expires_at: datetime,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> OAuthExchangeCode:
        """
        Create new OAuth exchange code.

        Args:
            code: Authorization code
            state: Associated state value
            expires_at: Code expiration time
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Created OAuthExchangeCode instance
        """
        return await self.create(
            code=code,
            state=state,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
            is_used=False,
        )

    async def validate_and_mark_used(
        self, code: str, state: str
    ) -> Optional[OAuthExchangeCode]:
        """
        Validate exchange code and mark as used.

        Checks:
        - Code exists
        - State matches
        - Not expired
        - Not already used

        Args:
            code: Authorization code
            state: State value

        Returns:
            OAuthExchangeCode instance if valid, None otherwise
        """
        stmt = select(OAuthExchangeCode).where(
            and_(
                OAuthExchangeCode.code == code,
                OAuthExchangeCode.state == state,
                OAuthExchangeCode.is_used == False,
                OAuthExchangeCode.expires_at > datetime.now(timezone.utc),
            )
        )
        result = await self.session.execute(stmt)
        code_obj = result.scalar_one_or_none()

        if not code_obj:
            return None

        # Mark as used
        await self.update(code_obj.id, is_used=True, used_at=datetime.now(timezone.utc))
        await self.session.refresh(code_obj)

        return code_obj

    async def cleanup_expired_codes(self) -> int:
        """
        Delete expired exchange codes.

        Returns:
            Number of codes deleted
        """
        stmt = select(OAuthExchangeCode).where(
            OAuthExchangeCode.expires_at <= datetime.now(timezone.utc)
        )
        result = await self.session.execute(stmt)
        codes = result.scalars().all()

        count = 0
        for code_obj in codes:
            await self.delete(code_obj.id)
            count += 1

        return count
