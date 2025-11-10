"""
Audit log repository for database operations.

Handles CRUD operations for AuditLog model.
Provides methods for logging security and system events.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditLog
from app.db.repositories.base import BaseRepository


class AuditLogRepository(BaseRepository[AuditLog]):
    """Repository for AuditLog model operations."""

    def __init__(self, session: AsyncSession):
        """Initialize audit log repository."""
        super().__init__(AuditLog, session)

    async def log_event(
        self,
        event_type: str,
        event_category: str,
        event_description: str,
        success: bool,
        user_id: Optional[int] = None,
        hh_user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        event_metadata: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ) -> AuditLog:
        """
        Log an audit event.

        Args:
            event_type: Type of event (e.g., 'login', 'logout', 'token_refresh')
            event_category: Category (e.g., 'auth', 'admin', 'error')
            event_description: Human-readable description
            success: Whether the event was successful
            user_id: User ID (if applicable)
            hh_user_id: HH user ID (if applicable)
            session_id: Session ID (if applicable)
            ip_address: Client IP address
            user_agent: Client user agent
            event_metadata: Additional context as JSON
            error_message: Error message (if failed)

        Returns:
            Created AuditLog instance

        Example:
            await audit_repo.log_event(
                event_type="login",
                event_category="auth",
                event_description="User successfully logged in",
                success=True,
                user_id=123,
                hh_user_id="174714255",
                ip_address="192.168.1.1",
            )
        """
        return await self.create(
            event_type=event_type,
            event_category=event_category,
            event_description=event_description,
            success=success,
            user_id=user_id,
            hh_user_id=hh_user_id,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            event_metadata=event_metadata,
            error_message=error_message,
        )

    async def log_login(
        self,
        user_id: int,
        hh_user_id: str,
        session_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> AuditLog:
        """
        Log login event.

        Args:
            user_id: User ID
            hh_user_id: HH user ID
            session_id: Session ID
            ip_address: Client IP address
            user_agent: Client user agent
            success: Whether login was successful
            error_message: Error message if failed

        Returns:
            Created AuditLog instance
        """
        return await self.log_event(
            event_type="login",
            event_category="auth",
            event_description=f"User {hh_user_id} login attempt",
            success=success,
            user_id=user_id,
            hh_user_id=hh_user_id,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            error_message=error_message,
        )

    async def log_logout(
        self,
        user_id: int,
        hh_user_id: str,
        session_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """
        Log logout event.

        Args:
            user_id: User ID
            hh_user_id: HH user ID
            session_id: Session ID
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Created AuditLog instance
        """
        return await self.log_event(
            event_type="logout",
            event_category="auth",
            event_description=f"User {hh_user_id} logged out",
            success=True,
            user_id=user_id,
            hh_user_id=hh_user_id,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def log_token_refresh(
        self,
        user_id: int,
        hh_user_id: str,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> AuditLog:
        """
        Log token refresh event.

        Args:
            user_id: User ID
            hh_user_id: HH user ID
            success: Whether refresh was successful
            error_message: Error message if failed

        Returns:
            Created AuditLog instance
        """
        return await self.log_event(
            event_type="token_refresh",
            event_category="auth",
            event_description=f"Token refresh for user {hh_user_id}",
            success=success,
            user_id=user_id,
            hh_user_id=hh_user_id,
            error_message=error_message,
        )

    async def log_admin_action(
        self,
        action_type: str,
        description: str,
        admin_username: str,
        ip_address: Optional[str] = None,
        event_metadata: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> AuditLog:
        """
        Log admin action.

        Args:
            action_type: Type of admin action
            description: Description of the action
            admin_username: Admin username
            ip_address: Admin IP address
            event_metadata: Additional context
            success: Whether action was successful
            error_message: Error message if failed

        Returns:
            Created AuditLog instance
        """
        return await self.log_event(
            event_type=action_type,
            event_category="admin",
            event_description=description,
            success=success,
            ip_address=ip_address,
            event_metadata={"admin_username": admin_username, **(event_metadata or {})},
            error_message=error_message,
        )

    async def log_security_event(
        self,
        event_type: str,
        description: str,
        hh_user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        event_metadata: Optional[Dict[str, Any]] = None,
        success: bool = False,
    ) -> AuditLog:
        """
        Log security event (e.g., failed login, invalid token).

        Args:
            event_type: Type of security event
            description: Description of the event
            hh_user_id: HH user ID (if applicable)
            ip_address: Client IP address
            event_metadata: Additional context
            success: Usually False for security events

        Returns:
            Created AuditLog instance
        """
        return await self.log_event(
            event_type=event_type,
            event_category="security",
            event_description=description,
            success=success,
            hh_user_id=hh_user_id,
            ip_address=ip_address,
            event_metadata=event_metadata,
        )

    async def get_user_logs(
        self,
        user_id: int,
        limit: Optional[int] = 100,
        event_category: Optional[str] = None,
    ) -> List[AuditLog]:
        """
        Get audit logs for a specific user.

        Args:
            user_id: User ID
            limit: Maximum number of logs to return
            event_category: Optional filter by category

        Returns:
            List of AuditLog instances
        """
        stmt = select(AuditLog).where(AuditLog.user_id == user_id)

        if event_category:
            stmt = stmt.where(AuditLog.event_category == event_category)

        stmt = stmt.order_by(AuditLog.created_at.desc())

        if limit:
            stmt = stmt.limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_logs_by_type(
        self,
        event_type: str,
        since: Optional[datetime] = None,
        limit: Optional[int] = 100,
    ) -> List[AuditLog]:
        """
        Get audit logs by event type.

        Args:
            event_type: Event type
            since: Only return logs after this time
            limit: Maximum number of logs to return

        Returns:
            List of AuditLog instances
        """
        stmt = select(AuditLog).where(AuditLog.event_type == event_type)

        if since:
            stmt = stmt.where(AuditLog.created_at >= since)

        stmt = stmt.order_by(AuditLog.created_at.desc())

        if limit:
            stmt = stmt.limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_failed_events(
        self,
        event_category: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: Optional[int] = 100,
    ) -> List[AuditLog]:
        """
        Get failed events.

        Useful for security monitoring.

        Args:
            event_category: Optional filter by category
            since: Only return logs after this time
            limit: Maximum number of logs to return

        Returns:
            List of AuditLog instances
        """
        stmt = select(AuditLog).where(AuditLog.success == False)

        if event_category:
            stmt = stmt.where(AuditLog.event_category == event_category)

        if since:
            stmt = stmt.where(AuditLog.created_at >= since)

        stmt = stmt.order_by(AuditLog.created_at.desc())

        if limit:
            stmt = stmt.limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def cleanup_old_logs(self, older_than_days: int = 90) -> int:
        """
        Delete old audit logs.

        Args:
            older_than_days: Delete logs older than this many days

        Returns:
            Number of logs deleted
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=older_than_days)

        stmt = select(AuditLog).where(AuditLog.created_at <= cutoff_date)
        result = await self.session.execute(stmt)
        logs = result.scalars().all()

        count = 0
        for log in logs:
            await self.delete(log.id)
            count += 1

        return count
