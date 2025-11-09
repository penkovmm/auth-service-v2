"""
Database connection and session management.

Provides async SQLAlchemy engine, session factory, and FastAPI dependency.
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    AsyncEngine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


# Declarative Base for all models
class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


# Global engine instance
_engine: AsyncEngine | None = None


def get_engine() -> AsyncEngine:
    """
    Get or create async SQLAlchemy engine.

    Returns:
        AsyncEngine: Async database engine

    Engine configuration:
    - Uses asyncpg driver for PostgreSQL
    - Connection pool: 5-20 connections
    - Echo SQL queries in debug mode
    - Statement timeout: 30 seconds
    """
    global _engine

    if _engine is None:
        settings = get_settings()

        # Determine pool class based on environment
        pool_class = NullPool if settings.environment == "test" else AsyncAdaptedQueuePool

        # Create async engine
        _engine = create_async_engine(
            settings.database_url,
            echo=settings.debug,  # Echo SQL queries in debug mode
            poolclass=pool_class,
            pool_size=5,  # Minimum pool size
            max_overflow=15,  # Maximum overflow connections
            pool_pre_ping=True,  # Verify connections before using
            pool_recycle=3600,  # Recycle connections after 1 hour
            connect_args={
                "server_settings": {
                    "application_name": settings.app_name,
                    "statement_timeout": "30000",  # 30 seconds
                },
            },
        )

        logger.info(
            "database_engine_created",
            database_url=settings.database_url.split("@")[-1],  # Hide credentials
            pool_size=5,
            max_overflow=15,
            environment=settings.environment,
        )

    return _engine


# Session factory
async_session_factory = async_sessionmaker(
    bind=get_engine(),  # Call get_engine() to get the engine instance
    class_=AsyncSession,
    expire_on_commit=False,  # Don't expire objects after commit
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions.

    Provides an async database session that automatically closes after use.

    Usage:
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            ...

    Yields:
        AsyncSession: Async database session

    Example:
        async with get_db() as session:
            result = await session.execute(select(User))
            users = result.scalars().all()
    """
    async with async_session_factory() as session:
        try:
            logger.debug("database_session_started")
            yield session
            await session.commit()
            logger.debug("database_session_committed")
        except Exception as e:
            await session.rollback()
            logger.error(
                "database_session_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise
        finally:
            await session.close()
            logger.debug("database_session_closed")


async def init_db() -> None:
    """
    Initialize database.

    Creates all tables defined in models.
    Should be used only in development/testing.
    In production, use Alembic migrations.

    Example:
        await init_db()
    """
    engine = get_engine()

    logger.info("database_initialization_started")

    async with engine.begin() as conn:
        # Import models to register them with Base
        from app.db import models  # noqa: F401

        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

    logger.info("database_initialization_completed")


async def close_db() -> None:
    """
    Close database connection.

    Disposes the engine and closes all connections.
    Should be called on application shutdown.

    Example:
        @app.on_event("shutdown")
        async def shutdown():
            await close_db()
    """
    global _engine

    if _engine is not None:
        logger.info("database_connection_closing")
        await _engine.dispose()
        _engine = None
        logger.info("database_connection_closed")
