"""
Application configuration using Pydantic Settings.

Loads configuration from environment variables (.env file).
"""

from typing import List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # === Application ===
    app_name: str = Field(default="HH Auth Service v2", description="Application name")
    app_version: str = Field(default="2.0.0", description="Application version")
    environment: str = Field(default="development", description="Environment (development/production)")
    debug: bool = Field(default=False, description="Debug mode")

    # === Server ===
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    workers: int = Field(default=1, description="Number of workers")

    # === Database ===
    database_url: str = Field(..., description="PostgreSQL connection URL")
    db_pool_size: int = Field(default=10, description="Database connection pool size")
    db_max_overflow: int = Field(default=20, description="Database max overflow connections")
    db_echo: bool = Field(default=False, description="Echo SQL queries")

    # === HeadHunter OAuth ===
    hh_client_id: str = Field(..., description="HH OAuth Client ID")
    hh_client_secret: str = Field(..., description="HH OAuth Client Secret")
    hh_app_token: str = Field(..., description="HH Application Token")
    hh_redirect_uri: str = Field(..., description="OAuth redirect URI")
    hh_user_agent: str = Field(..., description="User-Agent for HH API requests")

    # === Security ===
    encryption_key: str = Field(..., description="Fernet encryption key for tokens")
    session_expire_hours: int = Field(default=720, description="Session expiration time (hours)")
    exchange_code_expire_minutes: int = Field(default=5, description="Exchange code TTL (minutes)")
    oauth_state_expire_minutes: int = Field(default=10, description="OAuth state TTL (minutes)")

    # === Admin ===
    admin_username: str = Field(default="admin", description="Admin username for Basic Auth")
    admin_password: str = Field(..., description="Admin password hash (bcrypt)")

    # === Rate Limiting ===
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_storage: str = Field(default="memory", description="Rate limit storage backend")

    # === Logging ===
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format (json/text)")

    # === CORS ===
    cors_enabled: bool = Field(default=False, description="Enable CORS")
    cors_origins: List[str] = Field(default_factory=list, description="Allowed CORS origins")

    # === Monitoring ===
    metrics_enabled: bool = Field(default=True, description="Enable Prometheus metrics")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v_upper

    @field_validator("log_format")
    @classmethod
    def validate_log_format(cls, v: str) -> str:
        """Validate log format."""
        valid_formats = ["json", "text"]
        v_lower = v.lower()
        if v_lower not in valid_formats:
            raise ValueError(f"log_format must be one of {valid_formats}")
        return v_lower

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment."""
        valid_envs = ["development", "production", "testing"]
        v_lower = v.lower()
        if v_lower not in valid_envs:
            raise ValueError(f"environment must be one of {valid_envs}")
        return v_lower

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == "development"


# Singleton instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """
    Get application settings (singleton).

    Returns:
        Settings: Application settings instance
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


# Convenience export
settings = get_settings()
