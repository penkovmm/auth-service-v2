"""
Security utilities: encryption, decryption, authentication.

Provides:
- Token encryption/decryption using Fernet
- Basic HTTP authentication
- Password hashing and verification
"""

from cryptography.fernet import Fernet, InvalidToken
import bcrypt
from fastapi import HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
from typing import Tuple

from app.core.config import get_settings


class SecurityService:
    """Security service for encryption and authentication."""

    def __init__(self):
        """Initialize security service."""
        settings = get_settings()
        self.encryption_key = settings.encryption_key.encode()
        self.cipher = Fernet(self.encryption_key)
        self.admin_username = settings.admin_username
        self.admin_password_hash = settings.admin_password

    def encrypt_token(self, token: str) -> str:
        """
        Encrypt a token using Fernet symmetric encryption.

        Args:
            token: Plain text token to encrypt

        Returns:
            str: Encrypted token (base64 encoded)

        Raises:
            ValueError: If token is empty
        """
        if not token:
            raise ValueError("Token cannot be empty")

        token_bytes = token.encode()
        encrypted_bytes = self.cipher.encrypt(token_bytes)
        return encrypted_bytes.decode()

    def decrypt_token(self, encrypted_token: str) -> str:
        """
        Decrypt a token using Fernet symmetric encryption.

        Args:
            encrypted_token: Encrypted token (base64 encoded)

        Returns:
            str: Decrypted plain text token

        Raises:
            ValueError: If encrypted_token is empty or invalid
        """
        if not encrypted_token:
            raise ValueError("Encrypted token cannot be empty")

        try:
            encrypted_bytes = encrypted_token.encode()
            decrypted_bytes = self.cipher.decrypt(encrypted_bytes)
            return decrypted_bytes.decode()
        except InvalidToken as e:
            raise ValueError(f"Invalid or corrupted encrypted token: {e}")

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password using bcrypt.

        Args:
            password: Plain text password

        Returns:
            str: Bcrypt hash of the password

        Example:
            >>> hash = SecurityService.hash_password("my_password")
            >>> # hash: "$2b$12$..."
        """
        if not password:
            raise ValueError("Password cannot be empty")

        # Generate salt and hash password
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its bcrypt hash.

        Args:
            plain_password: Plain text password to verify
            hashed_password: Bcrypt hash to verify against

        Returns:
            bool: True if password matches, False otherwise
        """
        if not plain_password or not hashed_password:
            return False

        try:
            return bcrypt.checkpw(
                plain_password.encode('utf-8'),
                hashed_password.encode('utf-8')
            )
        except Exception:
            return False

    def verify_admin_credentials(self, username: str, password: str) -> bool:
        """
        Verify admin credentials.

        Args:
            username: Username to verify
            password: Password to verify

        Returns:
            bool: True if credentials are valid, False otherwise
        """
        # Constant-time comparison for username
        username_match = secrets.compare_digest(username, self.admin_username)

        # Verify password hash
        password_match = self.verify_password(password, self.admin_password_hash)

        return username_match and password_match


# Singleton instance
_security_service: SecurityService | None = None


def get_security_service() -> SecurityService:
    """
    Get security service instance (singleton).

    Returns:
        SecurityService: Security service instance
    """
    global _security_service
    if _security_service is None:
        _security_service = SecurityService()
    return _security_service


# FastAPI dependency for Basic Auth
security_scheme = HTTPBasic()


async def verify_admin(credentials: HTTPBasicCredentials) -> Tuple[str, str]:
    """
    FastAPI dependency to verify admin credentials using HTTP Basic Auth.

    Args:
        credentials: HTTP Basic credentials from request

    Returns:
        Tuple[str, str]: (username, password) if valid

    Raises:
        HTTPException: 401 if credentials are invalid

    Usage:
        @app.get("/admin/users", dependencies=[Depends(verify_admin)])
        async def get_users():
            ...
    """
    security_service = get_security_service()

    if not security_service.verify_admin_credentials(
        credentials.username, credentials.password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    return credentials.username, credentials.password


# Convenience exports
encrypt_token = lambda token: get_security_service().encrypt_token(token)
decrypt_token = lambda encrypted: get_security_service().decrypt_token(encrypted)
hash_password = SecurityService.hash_password
verify_password = SecurityService.verify_password
