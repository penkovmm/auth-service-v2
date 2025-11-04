"""
Token repository for database operations.

Handles CRUD operations for OAuthToken model.
"""

from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import OAuthToken
from app.db.repositories.base import BaseRepository


class TokenRepository(BaseRepository[OAuthToken]):
    """Repository for OAuthToken model operations."""

    def __init__(self, session: AsyncSession):
        """Initialize token repository."""
        super().__init__(OAuthToken, session)

    async def create_token(
        self,
        user_id: int,
        encrypted_access_token: str,
        encrypted_refresh_token: Optional[str] = None,
        token_type: str = "Bearer",
        expires_at: Optional[datetime] = None,
    ) -> OAuthToken:
        """
        Create new OAuth token.

        Args:
            user_id: User ID
            encrypted_access_token: Encrypted access token
            encrypted_refresh_token: Encrypted refresh token
            token_type: Token type (default: "Bearer")
            expires_at: Token expiration time

        Returns:
            Created OAuthToken instance
        """
        return await self.create(
            user_id=user_id,
            encrypted_access_token=encrypted_access_token,
            encrypted_refresh_token=encrypted_refresh_token,
            token_type=token_type,
            expires_at=expires_at,
            is_revoked=False,
        )

    async def get_active_token_by_user(self, user_id: int) -> Optional[OAuthToken]:
        """
        Get active (non-revoked, non-expired) token for user.

        Returns the most recent token if multiple exist.

        Args:
            user_id: User ID

        Returns:
            OAuthToken instance or None if not found
        """
        stmt = (
            select(OAuthToken)
            .where(
                and_(
                    OAuthToken.user_id == user_id,
                    OAuthToken.is_revoked == False,
                )
            )
            .order_by(OAuthToken.created_at.desc())
        )

        # Filter out expired tokens if expires_at is set
        result = await self.session.execute(stmt)
        tokens = result.scalars().all()

        for token in tokens:
            # If no expiration set, or not expired yet
            if token.expires_at is None or token.expires_at > datetime.utcnow():
                return token

        return None

    async def get_all_user_tokens(
        self, user_id: int, include_revoked: bool = False
    ) -> List[OAuthToken]:
        """
        Get all tokens for a user.

        Args:
            user_id: User ID
            include_revoked: If True, include revoked tokens

        Returns:
            List of OAuthToken instances
        """
        if include_revoked:
            stmt = select(OAuthToken).where(OAuthToken.user_id == user_id)
        else:
            stmt = select(OAuthToken).where(
                and_(OAuthToken.user_id == user_id, OAuthToken.is_revoked == False)
            )

        stmt = stmt.order_by(OAuthToken.created_at.desc())

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_token(
        self,
        token_id: int,
        encrypted_access_token: Optional[str] = None,
        encrypted_refresh_token: Optional[str] = None,
        expires_at: Optional[datetime] = None,
    ) -> Optional[OAuthToken]:
        """
        Update token (e.g., after refresh).

        Args:
            token_id: Token ID
            encrypted_access_token: New encrypted access token
            encrypted_refresh_token: New encrypted refresh token
            expires_at: New expiration time

        Returns:
            Updated OAuthToken instance or None if not found
        """
        update_data = {}

        if encrypted_access_token is not None:
            update_data["encrypted_access_token"] = encrypted_access_token
        if encrypted_refresh_token is not None:
            update_data["encrypted_refresh_token"] = encrypted_refresh_token
        if expires_at is not None:
            update_data["expires_at"] = expires_at

        if not update_data:
            return await self.get_by_id(token_id)

        return await self.update(token_id, **update_data)

    async def revoke_token(self, token_id: int) -> Optional[OAuthToken]:
        """
        Revoke token (set is_revoked=True).

        Args:
            token_id: Token ID

        Returns:
            Updated OAuthToken instance or None if not found
        """
        return await self.update(token_id, is_revoked=True)

    async def revoke_all_user_tokens(self, user_id: int) -> int:
        """
        Revoke all tokens for a user.

        Args:
            user_id: User ID

        Returns:
            Number of tokens revoked
        """
        stmt = select(OAuthToken).where(
            and_(OAuthToken.user_id == user_id, OAuthToken.is_revoked == False)
        )
        result = await self.session.execute(stmt)
        tokens = result.scalars().all()

        count = 0
        for token in tokens:
            await self.update(token.id, is_revoked=True)
            count += 1

        return count

    async def cleanup_expired_tokens(self) -> int:
        """
        Revoke expired tokens.

        Sets is_revoked=True for all expired tokens.

        Returns:
            Number of tokens revoked
        """
        stmt = select(OAuthToken).where(
            and_(
                OAuthToken.is_revoked == False,
                OAuthToken.expires_at <= datetime.utcnow(),
            )
        )
        result = await self.session.execute(stmt)
        tokens = result.scalars().all()

        count = 0
        for token in tokens:
            await self.update(token.id, is_revoked=True)
            count += 1

        return count

    async def delete_revoked_tokens(self, older_than_days: int = 30) -> int:
        """
        Delete old revoked tokens.

        Permanently deletes tokens that have been revoked for more than N days.

        Args:
            older_than_days: Delete tokens revoked more than this many days ago

        Returns:
            Number of tokens deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)

        stmt = select(OAuthToken).where(
            and_(
                OAuthToken.is_revoked == True, OAuthToken.updated_at <= cutoff_date
            )
        )
        result = await self.session.execute(stmt)
        tokens = result.scalars().all()

        count = 0
        for token in tokens:
            await self.delete(token.id)
            count += 1

        return count
