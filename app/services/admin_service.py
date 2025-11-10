"""
Admin service for administrative operations.

Handles whitelist management, user management, and audit logs.
"""

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.repositories.user import UserRepository, AllowedUserRepository
from app.db.repositories.audit import AuditLogRepository
from app.db.repositories.token import TokenRepository
from app.db.repositories.session import SessionRepository
from app.db.models import User, AllowedUser, AuditLog
from app.utils.exceptions import UserError, ValidationError

logger = get_logger(__name__)


class AdminService:
    """Service for administrative operations."""

    def __init__(self, session: AsyncSession):
        """
        Initialize admin service.

        Args:
            session: Async database session
        """
        self.session = session
        self.user_repo = UserRepository(session)
        self.allowed_user_repo = AllowedUserRepository(session)
        self.audit_repo = AuditLogRepository(session)
        self.token_repo = TokenRepository(session)
        self.session_repo = SessionRepository(session)

    # === Whitelist Management ===

    async def add_to_whitelist(
        self,
        hh_user_id: str,
        description: Optional[str] = None,
        added_by: str = "admin",
    ) -> AllowedUser:
        """
        Add user to whitelist.

        Args:
            hh_user_id: HH user ID
            description: Optional description
            added_by: Admin username

        Returns:
            AllowedUser: Created whitelist entry

        Raises:
            ValidationError: If user ID is invalid
        """
        if not hh_user_id or not hh_user_id.strip():
            raise ValidationError("HH user ID cannot be empty")

        # Check if already exists
        existing = await self.allowed_user_repo.get_by_hh_user_id(hh_user_id)
        if existing:
            if existing.is_active:
                logger.info("user_already_whitelisted", hh_user_id=hh_user_id)
                return existing
            else:
                # Reactivate
                await self.allowed_user_repo.update(existing.id, is_active=True)
                logger.info("user_reactivated_in_whitelist", hh_user_id=hh_user_id)
                return await self.allowed_user_repo.get_by_id(existing.id)

        # Add new user
        allowed_user = await self.allowed_user_repo.add_allowed_user(
            hh_user_id=hh_user_id,
            description=description,
            added_by=added_by,
        )

        logger.info(
            "user_added_to_whitelist",
            hh_user_id=hh_user_id,
            added_by=added_by,
        )

        return allowed_user

    async def remove_from_whitelist(self, hh_user_id: str) -> bool:
        """
        Remove user from whitelist.

        Args:
            hh_user_id: HH user ID

        Returns:
            bool: True if removed, False if not found
        """
        removed = await self.allowed_user_repo.remove_allowed_user(hh_user_id)

        if removed:
            logger.info("user_removed_from_whitelist", hh_user_id=hh_user_id)
        else:
            logger.warning("user_not_found_in_whitelist", hh_user_id=hh_user_id)

        return removed

    async def get_whitelist(
        self, active_only: bool = True, limit: Optional[int] = None
    ) -> List[AllowedUser]:
        """
        Get whitelist users.

        Args:
            active_only: If True, return only active users
            limit: Maximum number of users to return

        Returns:
            List[AllowedUser]: List of whitelist entries
        """
        users = await self.allowed_user_repo.get_all_allowed_users(
            active_only=active_only, limit=limit
        )

        logger.debug("whitelist_retrieved", count=len(users), active_only=active_only)

        return users

    async def is_user_whitelisted(self, hh_user_id: str) -> bool:
        """
        Check if user is in whitelist.

        Args:
            hh_user_id: HH user ID

        Returns:
            bool: True if whitelisted and active
        """
        is_allowed = await self.allowed_user_repo.is_user_allowed(hh_user_id)
        logger.debug("whitelist_check", hh_user_id=hh_user_id, is_allowed=is_allowed)
        return is_allowed

    # === User Management ===

    async def get_all_users(
        self, active_only: bool = False, limit: Optional[int] = None
    ) -> List[User]:
        """
        Get all users.

        Args:
            active_only: If True, return only active users
            limit: Maximum number of users to return

        Returns:
            List[User]: List of users
        """
        if active_only:
            users = await self.user_repo.get_active_users(limit=limit)
        else:
            users = await self.user_repo.get_all(limit=limit)

        logger.debug("users_retrieved", count=len(users), active_only=active_only)

        return users

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        Get user by ID.

        Args:
            user_id: User ID

        Returns:
            User: User instance or None
        """
        user = await self.user_repo.get_by_id(user_id)
        return user

    async def get_user_by_hh_id(self, hh_user_id: str) -> Optional[User]:
        """
        Get user by HH user ID.

        Args:
            hh_user_id: HH user ID

        Returns:
            User: User instance or None
        """
        user = await self.user_repo.get_by_hh_user_id(hh_user_id)
        return user

    async def deactivate_user(self, user_id: int) -> Optional[User]:
        """
        Deactivate user.

        Also revokes all tokens and sessions.

        Args:
            user_id: User ID

        Returns:
            User: Deactivated user or None if not found
        """
        user = await self.user_repo.deactivate_user(user_id)

        if user:
            # Revoke tokens and sessions
            await self.token_repo.revoke_all_user_tokens(user_id)
            await self.session_repo.revoke_all_user_sessions(user_id)

            logger.info("user_deactivated", user_id=user_id, hh_user_id=user.hh_user_id)

        return user

    async def activate_user(self, user_id: int) -> Optional[User]:
        """
        Activate user.

        Args:
            user_id: User ID

        Returns:
            User: Activated user or None if not found
        """
        user = await self.user_repo.activate_user(user_id)

        if user:
            logger.info("user_activated", user_id=user_id, hh_user_id=user.hh_user_id)

        return user

    # === Audit Logs ===

    async def get_user_audit_logs(
        self,
        user_id: int,
        limit: int = 100,
        event_category: Optional[str] = None,
    ) -> List[AuditLog]:
        """
        Get audit logs for a user.

        Args:
            user_id: User ID
            limit: Maximum number of logs to return
            event_category: Optional filter by category

        Returns:
            List[AuditLog]: List of audit logs
        """
        logs = await self.audit_repo.get_user_logs(
            user_id=user_id,
            limit=limit,
            event_category=event_category,
        )

        logger.debug("user_audit_logs_retrieved", user_id=user_id, count=len(logs))

        return logs

    async def get_failed_login_attempts(
        self, since_hours: int = 24, limit: int = 100
    ) -> List[AuditLog]:
        """
        Get failed login attempts.

        Args:
            since_hours: Get attempts from last N hours
            limit: Maximum number of logs to return

        Returns:
            List[AuditLog]: List of failed login attempts
        """
        from datetime import datetime, timedelta

        since = datetime.now(timezone.utc) - timedelta(hours=since_hours)

        logs = await self.audit_repo.get_failed_events(
            event_category="auth",
            since=since,
            limit=limit,
        )

        # Filter only login events
        login_failures = [log for log in logs if log.event_type == "login"]

        logger.debug(
            "failed_login_attempts_retrieved",
            count=len(login_failures),
            since_hours=since_hours,
        )

        return login_failures

    async def get_security_events(
        self, since_hours: int = 24, limit: int = 100
    ) -> List[AuditLog]:
        """
        Get security events.

        Args:
            since_hours: Get events from last N hours
            limit: Maximum number of logs to return

        Returns:
            List[AuditLog]: List of security events
        """
        from datetime import datetime, timedelta

        since = datetime.now(timezone.utc) - timedelta(hours=since_hours)

        logs = await self.audit_repo.get_failed_events(
            event_category="security",
            since=since,
            limit=limit,
        )

        logger.debug(
            "security_events_retrieved",
            count=len(logs),
            since_hours=since_hours,
        )

        return logs

    # === Statistics ===

    async def get_statistics(self) -> dict:
        """
        Get system statistics.

        Returns:
            dict: System statistics
        """
        stats = {
            "total_users": await self.user_repo.count(),
            "active_users": await self.user_repo.count({"is_active": True}),
            "whitelisted_users": await self.allowed_user_repo.count({"is_active": True}),
            "total_whitelist_entries": await self.allowed_user_repo.count(),
        }

        logger.debug("statistics_retrieved", **stats)

        return stats
