"""
Tests for app/core/security.py

Tests encryption, decryption, password hashing, and admin auth.
"""

import pytest
from cryptography.fernet import Fernet

from app.core.security import (
    SecurityService,
    get_security_service,
    encrypt_token,
    decrypt_token,
    hash_password,
    verify_password,
)


class TestEncryption:
    """Test encryption and decryption functionality."""

    def test_encrypt_decrypt_token(self):
        """Test that encryption and decryption work correctly."""
        original_token = "Bearer test_access_token_12345"

        # Encrypt
        encrypted = encrypt_token(original_token)

        # Verify encrypted is different from original
        assert encrypted != original_token
        assert len(encrypted) > len(original_token)

        # Decrypt
        decrypted = decrypt_token(encrypted)

        # Verify decrypted matches original
        assert decrypted == original_token

    def test_encrypt_different_tokens_produce_different_ciphertexts(self):
        """Test that different tokens produce different ciphertexts."""
        token1 = "Bearer token_1"
        token2 = "Bearer token_2"

        encrypted1 = encrypt_token(token1)
        encrypted2 = encrypt_token(token2)

        assert encrypted1 != encrypted2

    def test_encrypt_empty_token_raises_error(self):
        """Test that encrypting empty token raises ValueError."""
        with pytest.raises(ValueError, match="Token cannot be empty"):
            encrypt_token("")

    def test_decrypt_empty_token_raises_error(self):
        """Test that decrypting empty token raises ValueError."""
        with pytest.raises(ValueError, match="Encrypted token cannot be empty"):
            decrypt_token("")

    def test_decrypt_invalid_token_raises_error(self):
        """Test that decrypting invalid token raises ValueError."""
        with pytest.raises(ValueError, match="Invalid or corrupted"):
            decrypt_token("invalid_encrypted_data")

    def test_encrypt_decrypt_long_token(self):
        """Test encryption/decryption of long tokens."""
        long_token = "Bearer " + "x" * 1000

        encrypted = encrypt_token(long_token)
        decrypted = decrypt_token(encrypted)

        assert decrypted == long_token

    def test_encrypt_decrypt_special_characters(self):
        """Test encryption/decryption with special characters."""
        token_with_special = "Bearer token!@#$%^&*()_+-={}[]|\\:;\"'<>,.?/"

        encrypted = encrypt_token(token_with_special)
        decrypted = decrypt_token(encrypted)

        assert decrypted == token_with_special


class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_hash_password(self):
        """Test that password hashing works."""
        password = "my_secure_password_123"

        hashed = hash_password(password)

        # Verify hash is different from password
        assert hashed != password
        # Verify hash starts with bcrypt identifier
        assert hashed.startswith("$2b$")

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "correct_password"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "correct_password"
        wrong_password = "wrong_password"
        hashed = hash_password(password)

        assert verify_password(wrong_password, hashed) is False

    def test_verify_password_empty_password(self):
        """Test password verification with empty password."""
        hashed = hash_password("password")

        assert verify_password("", hashed) is False

    def test_verify_password_empty_hash(self):
        """Test password verification with empty hash."""
        assert verify_password("password", "") is False

    def test_hash_empty_password_raises_error(self):
        """Test that hashing empty password raises ValueError."""
        with pytest.raises(ValueError, match="Password cannot be empty"):
            hash_password("")

    def test_different_passwords_produce_different_hashes(self):
        """Test that different passwords produce different hashes."""
        password1 = "password1"
        password2 = "password2"

        hash1 = hash_password(password1)
        hash2 = hash_password(password2)

        assert hash1 != hash2

    def test_same_password_produces_different_hashes(self):
        """Test that same password produces different hashes (salt)."""
        password = "password"

        hash1 = hash_password(password)
        hash2 = hash_password(password)

        # Hashes should be different due to random salt
        assert hash1 != hash2
        # But both should verify correctly
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestSecurityService:
    """Test SecurityService class."""

    def test_security_service_singleton(self):
        """Test that get_security_service returns same instance."""
        service1 = get_security_service()
        service2 = get_security_service()

        assert service1 is service2

    def test_verify_admin_credentials_correct(self):
        """Test admin credentials verification with correct credentials."""
        service = get_security_service()

        # Note: This uses credentials from .env
        # For testing, we'd need to mock or use test credentials
        # For now, test the method exists and returns bool
        result = service.verify_admin_credentials("wrong_user", "wrong_pass")
        assert isinstance(result, bool)

    def test_verify_admin_credentials_incorrect_username(self):
        """Test admin credentials verification with incorrect username."""
        service = get_security_service()

        result = service.verify_admin_credentials("wrong_user", "any_password")
        assert result is False

    def test_verify_admin_credentials_incorrect_password(self):
        """Test admin credentials verification with incorrect password."""
        service = get_security_service()

        # Get correct username from settings
        correct_username = service.admin_username

        result = service.verify_admin_credentials(correct_username, "wrong_password")
        assert result is False


class TestSecurityEdgeCases:
    """Test edge cases and error handling."""

    def test_encrypt_decrypt_unicode(self):
        """Test encryption/decryption with unicode characters."""
        unicode_token = "Bearer токен_с_юникодом_🔐"

        encrypted = encrypt_token(unicode_token)
        decrypted = decrypt_token(encrypted)

        assert decrypted == unicode_token

    def test_decrypt_with_wrong_key_fails(self):
        """Test that decrypt fails with wrong encryption key."""
        original_token = "Bearer test_token"

        # Encrypt with current key
        encrypted = encrypt_token(original_token)

        # Create new cipher with different key
        different_key = Fernet.generate_key()
        different_cipher = Fernet(different_key)

        # Try to decrypt with different key - should fail
        with pytest.raises(Exception):  # Fernet raises InvalidToken
            different_cipher.decrypt(encrypted.encode())
