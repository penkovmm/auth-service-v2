"""
Custom exceptions for the application.

Provides specific exceptions for different error scenarios.
"""

from typing import Any, Dict


class AuthServiceException(Exception):
    """Base exception for all auth service errors."""

    def __init__(self, message: str, details: Dict[str, Any] | None = None):
        """
        Initialize exception.

        Args:
            message: Error message
            details: Additional error details
        """
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class ConfigurationError(AuthServiceException):
    """Raised when configuration is invalid or missing."""

    pass


class EncryptionError(AuthServiceException):
    """Raised when encryption/decryption fails."""

    pass


class OAuthError(AuthServiceException):
    """Base exception for OAuth-related errors."""

    pass


class OAuthStateError(OAuthError):
    """Raised when OAuth state is invalid or expired."""

    pass


class OAuthCodeError(OAuthError):
    """Raised when OAuth authorization code is invalid."""

    pass


class TokenError(AuthServiceException):
    """Base exception for token-related errors."""

    pass


class TokenExpiredError(TokenError):
    """Raised when token has expired."""

    pass


class TokenRefreshError(TokenError):
    """Raised when token refresh fails."""

    pass


class SessionError(AuthServiceException):
    """Base exception for session-related errors."""

    pass


class SessionNotFoundError(SessionError):
    """Raised when session is not found."""

    pass


class SessionExpiredError(SessionError):
    """Raised when session has expired."""

    pass


class UserError(AuthServiceException):
    """Base exception for user-related errors."""

    pass


class UserNotFoundError(UserError):
    """Raised when user is not found."""

    pass


class UserNotWhitelistedError(UserError):
    """Raised when user is not in whitelist."""

    pass


class HeadHunterAPIError(AuthServiceException):
    """Raised when HeadHunter API request fails."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_data: Dict[str, Any] | None = None,
    ):
        """
        Initialize HH API error.

        Args:
            message: Error message
            status_code: HTTP status code from HH API
            response_data: Response data from HH API
        """
        details = {"status_code": status_code, "response_data": response_data}
        super().__init__(message, details)
        self.status_code = status_code
        self.response_data = response_data


class DatabaseError(AuthServiceException):
    """Raised when database operation fails."""

    pass


class ValidationError(AuthServiceException):
    """Raised when data validation fails."""

    pass
