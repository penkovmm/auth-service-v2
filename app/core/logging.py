"""
Structured logging configuration using structlog.

Provides JSON-formatted logs with context and filters sensitive data.
"""

import logging
import sys
from typing import Any, Dict
import structlog
from structlog.types import EventDict, Processor

from app.core.config import get_settings


# List of sensitive keys that should never be logged
SENSITIVE_KEYS = {
    "access_token",
    "refresh_token",
    "encrypted_token",
    "token",
    "password",
    "secret",
    "encryption_key",
    "admin_password",
    "client_secret",
    "api_key",
}


def filter_sensitive_data(logger: logging.Logger, method_name: str, event_dict: EventDict) -> EventDict:
    """
    Filter sensitive data from logs.

    Replaces values of sensitive keys with "***REDACTED***".

    Args:
        logger: Logger instance
        method_name: Method name
        event_dict: Event dictionary to filter

    Returns:
        EventDict: Filtered event dictionary
    """
    def _filter_dict(data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively filter sensitive keys from dictionary."""
        filtered = {}
        for key, value in data.items():
            # Check if key is sensitive (case-insensitive)
            if any(sensitive_key in key.lower() for sensitive_key in SENSITIVE_KEYS):
                filtered[key] = "***REDACTED***"
            elif isinstance(value, dict):
                filtered[key] = _filter_dict(value)
            elif isinstance(value, list):
                filtered[key] = [
                    _filter_dict(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                filtered[key] = value
        return filtered

    return _filter_dict(event_dict)


def add_app_context(logger: logging.Logger, method_name: str, event_dict: EventDict) -> EventDict:
    """
    Add application context to log events.

    Args:
        logger: Logger instance
        method_name: Method name
        event_dict: Event dictionary

    Returns:
        EventDict: Event dictionary with app context
    """
    settings = get_settings()
    event_dict["app_name"] = settings.app_name
    event_dict["app_version"] = settings.app_version
    event_dict["environment"] = settings.environment
    return event_dict


def setup_logging() -> None:
    """
    Configure structured logging for the application.

    Sets up structlog with:
    - JSON or text formatting based on settings
    - Sensitive data filtering
    - Appropriate log level
    - Application context
    """
    settings = get_settings()

    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level),
    )

    # Processors for structlog
    processors: list[Processor] = [
        # Add log level
        structlog.stdlib.add_log_level,
        # Add logger name
        structlog.stdlib.add_logger_name,
        # Add timestamp
        structlog.processors.TimeStamper(fmt="iso"),
        # Add application context
        add_app_context,
        # Filter sensitive data (IMPORTANT!)
        filter_sensitive_data,
        # Stack info for exceptions
        structlog.processors.StackInfoRenderer(),
        # Format exceptions
        structlog.processors.format_exc_info,
    ]

    # Add appropriate renderer based on format
    if settings.log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:  # text
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.BoundLogger:
    """
    Get a configured logger instance.

    Args:
        name: Logger name (usually __name__)

    Returns:
        BoundLogger: Configured structlog logger

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("user_logged_in", user_id=123, email="user@example.com")
    """
    return structlog.get_logger(name)


# Configure logging on module import
setup_logging()
