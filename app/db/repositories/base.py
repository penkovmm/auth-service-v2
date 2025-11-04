"""
Base repository with generic CRUD operations.

Provides common database operations for all repositories.
"""

from typing import TypeVar, Generic, Type, Optional, List, Any, Dict
from sqlalchemy import select, delete, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Base repository with common CRUD operations.

    Generic repository that can be inherited by specific model repositories.
    Provides async CRUD operations using SQLAlchemy 2.0 syntax.
    """

    def __init__(self, model: Type[ModelType], session: AsyncSession):
        """
        Initialize repository.

        Args:
            model: SQLAlchemy model class
            session: Async database session
        """
        self.model = model
        self.session = session

    async def get_by_id(self, id: int) -> Optional[ModelType]:
        """
        Get record by ID.

        Args:
            id: Record ID

        Returns:
            Model instance or None if not found
        """
        stmt = select(self.model).where(self.model.id == id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_field(
        self, field_name: str, field_value: Any
    ) -> Optional[ModelType]:
        """
        Get record by specific field.

        Args:
            field_name: Field name
            field_value: Field value

        Returns:
            Model instance or None if not found
        """
        field = getattr(self.model, field_name)
        stmt = select(self.model).where(field == field_value)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> List[ModelType]:
        """
        Get all records with optional pagination.

        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            List of model instances
        """
        stmt = select(self.model)

        if offset is not None:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_filters(
        self, filters: Dict[str, Any], limit: Optional[int] = None
    ) -> List[ModelType]:
        """
        Get records by multiple filters.

        Args:
            filters: Dictionary of field_name: field_value
            limit: Maximum number of records to return

        Returns:
            List of model instances
        """
        stmt = select(self.model)

        for field_name, field_value in filters.items():
            field = getattr(self.model, field_name)
            stmt = stmt.where(field == field_value)

        if limit is not None:
            stmt = stmt.limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, **kwargs) -> ModelType:
        """
        Create new record.

        Args:
            **kwargs: Field values for the new record

        Returns:
            Created model instance
        """
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def update(self, id: int, **kwargs) -> Optional[ModelType]:
        """
        Update record by ID.

        Args:
            id: Record ID
            **kwargs: Fields to update

        Returns:
            Updated model instance or None if not found
        """
        stmt = (
            update(self.model).where(self.model.id == id).values(**kwargs).returning(self.model)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.scalar_one_or_none()

    async def delete(self, id: int) -> bool:
        """
        Delete record by ID.

        Args:
            id: Record ID

        Returns:
            True if deleted, False if not found
        """
        stmt = delete(self.model).where(self.model.id == id)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0

    async def delete_by_field(self, field_name: str, field_value: Any) -> int:
        """
        Delete records by field value.

        Args:
            field_name: Field name
            field_value: Field value

        Returns:
            Number of deleted records
        """
        field = getattr(self.model, field_name)
        stmt = delete(self.model).where(field == field_value)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount

    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count records with optional filters.

        Args:
            filters: Optional dictionary of field_name: field_value

        Returns:
            Number of matching records
        """
        stmt = select(func.count()).select_from(self.model)

        if filters:
            for field_name, field_value in filters.items():
                field = getattr(self.model, field_name)
                stmt = stmt.where(field == field_value)

        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def exists(self, filters: Dict[str, Any]) -> bool:
        """
        Check if record exists with given filters.

        Args:
            filters: Dictionary of field_name: field_value

        Returns:
            True if at least one matching record exists
        """
        count = await self.count(filters)
        return count > 0
