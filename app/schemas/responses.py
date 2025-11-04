"""
Pydantic response schemas for API endpoints.

Defines response models for all API endpoints.
"""

from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field, ConfigDict


# === Base Schemas ===


class BaseResponse(BaseModel):
    """Base response model."""

    model_config = ConfigDict(from_attributes=True)


# === User Schemas ===


class UserResponse(BaseResponse):
    """User response schema."""

    id: int
    hh_user_id: str
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None


class UserListResponse(BaseResponse):
    """List of users response."""

    users: List[UserResponse]
    total: int


# === Whitelist Schemas ===


class AllowedUserResponse(BaseResponse):
    """Allowed user (whitelist) response schema."""

    id: int
    hh_user_id: str
    description: Optional[str] = None
    added_by: Optional[str] = None
    is_active: bool
    created_at: datetime


class WhitelistResponse(BaseResponse):
    """Whitelist response."""

    allowed_users: List[AllowedUserResponse]
    total: int


# === Session Schemas ===


class SessionResponse(BaseResponse):
    """Session response schema."""

    session_id: str
    user_id: int
    ip_address: Optional[str] = None
    is_active: bool
    created_at: datetime
    expires_at: datetime
    last_activity_at: datetime


class SessionListResponse(BaseResponse):
    """List of sessions response."""

    sessions: List[SessionResponse]
    total: int


# === OAuth Schemas ===


class OAuthURLResponse(BaseResponse):
    """OAuth authorization URL response."""

    authorization_url: str = Field(..., description="HeadHunter OAuth authorization URL")
    state: str = Field(..., description="CSRF protection state value")


class LoginSuccessResponse(BaseResponse):
    """Successful login response."""

    message: str = "Login successful"
    session_id: str
    user: UserResponse


class LogoutResponse(BaseResponse):
    """Logout response."""

    message: str = "Logout successful"


# === Audit Log Schemas ===


class AuditLogResponse(BaseResponse):
    """Audit log response schema."""

    id: int
    event_type: str
    event_category: str
    event_description: str
    user_id: Optional[int] = None
    hh_user_id: Optional[str] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    success: bool
    error_message: Optional[str] = None
    event_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime


class AuditLogListResponse(BaseResponse):
    """List of audit logs response."""

    logs: List[AuditLogResponse]
    total: int


# === Admin Schemas ===


class StatisticsResponse(BaseResponse):
    """System statistics response."""

    total_users: int
    active_users: int
    whitelisted_users: int
    total_whitelist_entries: int


# === Error Schemas ===


class ErrorDetail(BaseModel):
    """Error detail schema."""

    field: Optional[str] = None
    message: str


class ErrorResponse(BaseModel):
    """Error response schema."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[List[ErrorDetail]] = None


# === Success Schemas ===


class MessageResponse(BaseResponse):
    """Generic message response."""

    message: str


class SuccessResponse(BaseResponse):
    """Generic success response."""

    success: bool = True
    message: Optional[str] = None


# === Health Check Schemas ===


class HealthCheckResponse(BaseResponse):
    """Health check response."""

    status: str = Field(..., description="Service status: healthy, degraded, unhealthy")
    version: str
    environment: str
    database: str = Field(..., description="Database status: connected, disconnected")
    timestamp: datetime
