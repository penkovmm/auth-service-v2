"""
Pytest configuration and fixtures.

Provides common fixtures for testing.
"""

import pytest
from cryptography.fernet import Fernet
import os


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """
    Set up test environment variables.

    Runs once per test session.
    """
    # Ensure we're using test encryption key
    test_encryption_key = Fernet.generate_key().decode()

    # Set minimal required env vars for testing
    os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
    os.environ.setdefault("HH_CLIENT_ID", "test_client_id")
    os.environ.setdefault("HH_CLIENT_SECRET", "test_client_secret")
    os.environ.setdefault("HH_APP_TOKEN", "test_app_token")
    os.environ.setdefault("HH_REDIRECT_URI", "http://localhost:5555/callback")
    os.environ.setdefault("HH_USER_AGENT", "Test Agent")
    os.environ.setdefault("ENCRYPTION_KEY", test_encryption_key)
    os.environ.setdefault("ADMIN_USERNAME", "test_admin")
    os.environ.setdefault("ADMIN_PASSWORD", "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5aeJ.Qnm4tONO")  # hash of "admin"

    yield

    # Cleanup after tests (if needed)


@pytest.fixture
def sample_token():
    """Provide a sample token for testing."""
    return "Bearer sample_access_token_for_testing_12345"


@pytest.fixture
def sample_refresh_token():
    """Provide a sample refresh token for testing."""
    return "sample_refresh_token_67890"


@pytest.fixture
def sample_password():
    """Provide a sample password for testing."""
    return "test_password_123"


@pytest.fixture
def sample_hh_user_id():
    """Provide a sample HH user ID for testing."""
    return "174714255"


@pytest.fixture
def sample_user_data():
    """Provide sample user data for testing."""
    return {
        "hh_user_id": "174714255",
        "email": "test@example.com",
        "first_name": "Test",
        "last_name": "User",
    }
