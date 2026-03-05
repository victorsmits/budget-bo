"""Security utilities: Encryption service using AES-256 (Fernet)."""

import base64
import hashlib
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings


class EncryptionService:
    """
    Service for encrypting and decrypting sensitive data using AES-256.
    Uses Fernet (symmetric encryption) with keys derived from application secret.
    """

    _instance: Optional["EncryptionService"] = None
    _fernet: Optional[Fernet] = None

    def __new__(cls) -> "EncryptionService":
        """Singleton pattern to ensure single Fernet instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        """Initialize Fernet with derived key."""
        settings = get_settings()
        key = self._derive_key(settings.encryption_key)
        self._fernet = Fernet(key)

    @staticmethod
    def _derive_key(secret: str) -> bytes:
        """
        Derive a 32-byte URL-safe base64-encoded key from secret.
        Fernet requires a 32-byte key, base64-encoded to 44 bytes.
        """
        # Hash the secret to get 32 bytes
        key_bytes = hashlib.sha256(secret.encode()).digest()
        # Encode to base64 for Fernet
        return base64.urlsafe_b64encode(key_bytes)

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext string.

        Args:
            plaintext: String to encrypt

        Returns:
            Base64-encoded encrypted string

        Raises:
            ValueError: If encryption fails
        """
        if self._fernet is None:
            raise RuntimeError("Encryption service not initialized")

        try:
            encoded = plaintext.encode("utf-8")
            encrypted = self._fernet.encrypt(encoded)
            return encrypted.decode("utf-8")
        except Exception as e:
            raise ValueError(f"Encryption failed: {e}") from e

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt ciphertext string.

        Args:
            ciphertext: Base64-encoded encrypted string

        Returns:
            Decrypted plaintext string

        Raises:
            ValueError: If decryption fails or token is invalid
        """
        if self._fernet is None:
            raise RuntimeError("Encryption service not initialized")

        try:
            encoded = ciphertext.encode("utf-8")
            decrypted = self._fernet.decrypt(encoded)
            return decrypted.decode("utf-8")
        except InvalidToken as e:
            raise ValueError("Invalid or corrupted encrypted data") from e
        except Exception as e:
            raise ValueError(f"Decryption failed: {e}") from e

    def rotate_key(self, new_secret: str, encrypted_data: list[str]) -> list[str]:
        """
        Re-encrypt data with a new key.
        Useful for key rotation scenarios.

        Args:
            new_secret: New encryption secret
            encrypted_data: List of encrypted strings to re-encrypt

        Returns:
            List of re-encrypted strings
        """
        # Decrypt all with current key
        decrypted = []
        for data in encrypted_data:
            try:
                decrypted.append(self.decrypt(data))
            except ValueError:
                # Skip corrupted data
                continue

        # Create new encryption service with new key
        new_key = self._derive_key(new_secret)
        new_fernet = Fernet(new_key)

        # Re-encrypt with new key
        re_encrypted = []
        for data in decrypted:
            encoded = data.encode("utf-8")
            encrypted = new_fernet.encrypt(encoded)
            re_encrypted.append(encrypted.decode("utf-8"))

        return re_encrypted


def get_encryption_service() -> EncryptionService:
    """Get singleton instance of EncryptionService."""
    return EncryptionService()
