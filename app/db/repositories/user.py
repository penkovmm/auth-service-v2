"""
User repository for database operations.

Handles CRUD operations for User and AllowedUser models.
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, AllowedUser
from app.db.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User model operations."""

    def __init__(self, session: AsyncSession):
        """Initialize user repository."""
        super().__init__(User, session)

    async def get_by_hh_user_id(self, hh_user_id: str) -> Optional[User]:
        """
        Get user by HeadHunter user ID.

        Args:
            hh_user_id: HeadHunter user ID

        Returns:
            User instance or None if not found
        """
        return await self.get_by_field("hh_user_id", hh_user_id)

    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email.

        Args:
            email: User email

        Returns:
            User instance or None if not found
        """
        return await self.get_by_field("email", email)

    async def create_user(
        self,
        hh_user_id: str,
        email: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        middle_name: Optional[str] = None,
    ) -> User:
        """
        Create new user.

        Args:
            hh_user_id: HeadHunter user ID
            email: User email
            first_name: First name
            last_name: Last name
            middle_name: Middle name

        Returns:
            Created User instance
        """
        return await self.create(
            hh_user_id=hh_user_id,
            email=email,
            first_name=first_name,
            last_name=last_name,
            middle_name=middle_name,
            is_active=True,
            last_login_at=datetime.utcnow(),
        )

    async def update_last_login(self, user_id: int) -> Optional[User]:
        """
        Update user's last login timestamp.

        Args:
            user_id: User ID

        Returns:
            Updated User instance or None if not found
        """
        return await self.update(user_id, last_login_at=datetime.utcnow())

    async def update_user_info(
        self,
        user_id: int,
        email: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        middle_name: Optional[str] = None,
    ) -> Optional[User]:
        """
        Update user information.

        Args:
            user_id: User ID
            email: New email
            first_name: New first name
            last_name: New last name
            middle_name: New middle name

        Returns:
            Updated User instance or None if not found
        """
        update_data = {}
        if email is not None:
            update_data["email"] = email
        if first_name is not None:
            update_data["first_name"] = first_name
        if last_name is not None:
            update_data["last_name"] = last_name
        if middle_name is not None:
            update_data["middle_name"] = middle_name

        if not update_data:
            return await self.get_by_id(user_id)

        return await self.update(user_id, **update_data)

    async def deactivate_user(self, user_id: int) -> Optional[User]:
        """
        Deactivate user.

        Args:
            user_id: User ID

        Returns:
            Updated User instance or None if not found
        """
        return await self.update(user_id, is_active=False)

    async def activate_user(self, user_id: int) -> Optional[User]:
        """
        Activate user.

        Args:
            user_id: User ID

        Returns:
            Updated User instance or None if not found
        """
        return await self.update(user_id, is_active=True)

    async def get_active_users(self, limit: Optional[int] = None) -> List[User]:
        """
        Get all active users.

        Args:
            limit: Maximum number of users to return

        Returns:
            List of active User instances
        """
        return await self.get_by_filters({"is_active": True}, limit=limit)


class AllowedUserRepository(BaseRepository[AllowedUser]):
    """Repository for AllowedUser model operations (whitelist)."""

    def __init__(self, session: AsyncSession):
        """Initialize allowed user repository."""
        super().__init__(AllowedUser, session)

    async def is_user_allowed(self, hh_user_id: str) -> bool:
        """
        Check if user is in whitelist and active.

        Args:
            hh_user_id: HeadHunter user ID

        Returns:
            True if user is allowed, False otherwise
        """
        stmt = select(AllowedUser).where(
            AllowedUser.hh_user_id == hh_user_id, AllowedUser.is_active == True
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_by_hh_user_id(self, hh_user_id: str) -> Optional[AllowedUser]:
        """
        Get allowed user by HH user ID.

        Args:
            hh_user_id: HeadHunter user ID

        Returns:
            AllowedUser instance or None if not found
        """
        return await self.get_by_field("hh_user_id", hh_user_id)

    async def add_allowed_user(
        self,
        hh_user_id: str,
        description: Optional[str] = None,
        added_by: Optional[str] = None,
    ) -> AllowedUser:
        """
        Add user to whitelist.

        Args:
            hh_user_id: HeadHunter user ID
            description: Optional description
            added_by: Who added this user

        Returns:
            Created AllowedUser instance
        """
        return await self.create(
            hh_user_id=hh_user_id,
            description=description,
            added_by=added_by,
            is_active=True,
        )

    async def remove_allowed_user(self, hh_user_id: str) -> bool:
        """
        Remove user from whitelist (soft delete - set is_active=False).

        Args:
            hh_user_id: HeadHunter user ID

        Returns:
            True if updated, False if not found
        """
        allowed_user = await self.get_by_hh_user_id(hh_user_id)
        if not allowed_user:
            return False

        await self.update(allowed_user.id, is_active=False)
        return True

    async def get_all_allowed_users(
        self, active_only: bool = True, limit: Optional[int] = None
    ) -> List[AllowedUser]:
        """
        Get all allowed users.

        Args:
            active_only: If True, return only active users
            limit: Maximum number of users to return

        Returns:
            List of AllowedUser instances
        """
        if active_only:
            return await self.get_by_filters({"is_active": True}, limit=limit)
        else:
            return await self.get_all(limit=limit)
