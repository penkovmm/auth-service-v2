"""
Schemas package.

Pydantic models for request/response validation.
"""

from app.schemas.requests import (
    AddToWhitelistRequest,
    RemoveFromWhitelistRequest,
)
from app.schemas.responses import (
    UserResponse,
    UserListResponse,
    AllowedUserResponse,
    WhitelistResponse,
    SessionResponse,
    SessionListResponse,
    OAuthURLResponse,
    LoginSuccessResponse,
    LogoutResponse,
    AuditLogResponse,
    AuditLogListResponse,
    StatisticsResponse,
    ErrorResponse,
    ErrorDetail,
    MessageResponse,
    SuccessResponse,
    HealthCheckResponse,
)

__all__ = [
    # Requests
    "AddToWhitelistRequest",
    "RemoveFromWhitelistRequest",
    # Responses
    "UserResponse",
    "UserListResponse",
    "AllowedUserResponse",
    "WhitelistResponse",
    "SessionResponse",
    "SessionListResponse",
    "OAuthURLResponse",
    "LoginSuccessResponse",
    "LogoutResponse",
    "AuditLogResponse",
    "AuditLogListResponse",
    "StatisticsResponse",
    "ErrorResponse",
    "ErrorDetail",
    "MessageResponse",
    "SuccessResponse",
    "HealthCheckResponse",
]
