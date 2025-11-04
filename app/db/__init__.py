"""
Database package.

Provides database connection, models, and repositories.
"""

from app.db.database import get_db, get_engine, Base, init_db, close_db
from app.db.models import (
    User,
    UserSession,
    OAuthToken,
    OAuthExchangeCode,
    OAuthState,
    AllowedUser,
    AuditLog,
)

__all__ = [
    # Database
    "get_db",
    "get_engine",
    "Base",
    "init_db",
    "close_db",
    # Models
    "User",
    "UserSession",
    "OAuthToken",
    "OAuthExchangeCode",
    "OAuthState",
    "AllowedUser",
    "AuditLog",
]
