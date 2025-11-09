"""
Schemas package.

Pydantic models for request/response validation.
"""

from app.schemas.requests import (
    AddToWhitelistRequest,
    RemoveFromWhitelistRequest,
    GetTokenRequest,
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
    TokenResponse,
)

__all__ = [
    # Requests
    "AddToWhitelistRequest",
    "RemoveFromWhitelistRequest",
    "GetTokenRequest",
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
    "TokenResponse",
]
