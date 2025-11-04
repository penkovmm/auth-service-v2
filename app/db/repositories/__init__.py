"""
Repositories package.

Provides data access layer for all models.
"""

from app.db.repositories.base import BaseRepository
from app.db.repositories.user import UserRepository, AllowedUserRepository
from app.db.repositories.session import (
    SessionRepository,
    OAuthStateRepository,
    OAuthExchangeCodeRepository,
)
from app.db.repositories.token import TokenRepository
from app.db.repositories.audit import AuditLogRepository

__all__ = [
    # Base
    "BaseRepository",
    # User
    "UserRepository",
    "AllowedUserRepository",
    # Session
    "SessionRepository",
    "OAuthStateRepository",
    "OAuthExchangeCodeRepository",
    # Token
    "TokenRepository",
    # Audit
    "AuditLogRepository",
]
