"""
SQLAlchemy database models.

Defines all database tables and relationships.
"""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    String,
    Integer,
    DateTime,
    Text,
    Boolean,
    Index,
    UniqueConstraint,
    ForeignKey,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.database import Base


class User(Base):
    """
    User model - stores HeadHunter user information.

    Represents authenticated HH users in the system.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hh_user_id: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    middle_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    sessions: Mapped[list["UserSession"]] = relationship(
        "UserSession", back_populates="user", cascade="all, delete-orphan"
    )
    tokens: Mapped[list["OAuthToken"]] = relationship(
        "OAuthToken", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, hh_user_id={self.hh_user_id}, email={self.email})>"


class UserSession(Base):
    """
    User session model - tracks active user sessions.

    Each successful login creates a new session.
    Sessions can be revoked individually.
    """

    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="sessions")

    # Indexes
    __table_args__ = (
        Index("ix_user_sessions_user_id_is_active", "user_id", "is_active"),
        Index("ix_user_sessions_expires_at", "expires_at"),
    )

    @property
    def is_valid(self) -> bool:
        """Check if session is valid (active and not expired)."""
        return self.is_active and self.expires_at > datetime.now(timezone.utc)

    def __repr__(self) -> str:
        return f"<UserSession(id={self.id}, session_id={self.session_id}, user_id={self.user_id})>"


class OAuthToken(Base):
    """
    OAuth token model - stores encrypted HH access and refresh tokens.

    Tokens are encrypted at rest using Fernet encryption.
    Each user can have multiple token sets (for different sessions).
    """

    __tablename__ = "oauth_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Encrypted tokens (base64-encoded Fernet ciphertext)
    encrypted_access_token: Mapped[str] = mapped_column(Text, nullable=False)
    encrypted_refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Token metadata
    token_type: Mapped[str] = mapped_column(
        String(50), default="Bearer", nullable=False
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="tokens")

    # Indexes
    __table_args__ = (
        Index("ix_oauth_tokens_user_id_is_revoked", "user_id", "is_revoked"),
        Index("ix_oauth_tokens_expires_at", "expires_at"),
    )

    def __repr__(self) -> str:
        return f"<OAuthToken(id={self.id}, user_id={self.user_id}, expires_at={self.expires_at})>"


class OAuthExchangeCode(Base):
    """
    OAuth exchange code model - temporary storage for authorization codes.

    Stores codes received from HH before exchange for tokens.
    Codes expire after 10 minutes or after successful exchange.
    """

    __tablename__ = "oauth_exchange_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(
        String(500), unique=True, nullable=False, index=True
    )
    state: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # IP and user agent for security audit
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    is_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Indexes
    __table_args__ = (Index("ix_oauth_exchange_codes_expires_at", "expires_at"),)

    def __repr__(self) -> str:
        return f"<OAuthExchangeCode(id={self.id}, state={self.state}, is_used={self.is_used})>"


class OAuthState(Base):
    """
    OAuth state model - CSRF protection for OAuth flow.

    Stores random state values to prevent CSRF attacks.
    States expire after 10 minutes.
    """

    __tablename__ = "oauth_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    state: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )

    # IP and user agent for security audit
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    is_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Indexes
    __table_args__ = (Index("ix_oauth_states_expires_at", "expires_at"),)

    def __repr__(self) -> str:
        return f"<OAuthState(id={self.id}, state={self.state}, is_used={self.is_used})>"


class AllowedUser(Base):
    """
    Allowed user model - whitelist of permitted HH user IDs.

    Only users in this whitelist can authenticate.
    Can be managed via admin API.
    """

    __tablename__ = "allowed_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hh_user_id: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )

    # Optional metadata about the user
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    added_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Indexes
    __table_args__ = (Index("ix_allowed_users_is_active", "is_active"),)

    def __repr__(self) -> str:
        return f"<AllowedUser(id={self.id}, hh_user_id={self.hh_user_id}, is_active={self.is_active})>"


class AuditLog(Base):
    """
    Audit log model - tracks important system events.

    Records authentication events, admin actions, errors, etc.
    Provides audit trail for security and compliance.
    """

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Event details
    event_type: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )  # e.g., 'login', 'logout', 'token_refresh', 'admin_action'
    event_category: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # e.g., 'auth', 'admin', 'error'
    event_description: Mapped[str] = mapped_column(Text, nullable=False)

    # User and session info
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    hh_user_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Request info
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Additional context (JSON field)
    event_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Success/failure
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    # Indexes for common queries
    __table_args__ = (
        Index("ix_audit_logs_event_type_created_at", "event_type", "created_at"),
        Index("ix_audit_logs_user_id_created_at", "user_id", "created_at"),
        Index("ix_audit_logs_category_created_at", "event_category", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, event_type={self.event_type}, success={self.success})>"
