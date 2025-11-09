"""
Pydantic request schemas for API endpoints.

Defines request models for all API endpoints.
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator


# === Admin Request Schemas ===


class AddToWhitelistRequest(BaseModel):
    """Add user to whitelist request."""

    hh_user_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="HeadHunter user ID",
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="Optional description of the user",
    )

    @field_validator("hh_user_id")
    @classmethod
    def validate_hh_user_id(cls, v: str) -> str:
        """Validate HH user ID is not empty after stripping."""
        v = v.strip()
        if not v:
            raise ValueError("HH user ID cannot be empty")
        return v


class RemoveFromWhitelistRequest(BaseModel):
    """Remove user from whitelist request."""

    hh_user_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="HeadHunter user ID",
    )

    @field_validator("hh_user_id")
    @classmethod
    def validate_hh_user_id(cls, v: str) -> str:
        """Validate HH user ID is not empty after stripping."""
        v = v.strip()
        if not v:
            raise ValueError("HH user ID cannot be empty")
        return v


# === Token Requests ===


class GetTokenRequest(BaseModel):
    """Get HH access token request."""

    session_id: str = Field(
        ...,
        min_length=1,
        description="Session ID from successful OAuth login",
    )
