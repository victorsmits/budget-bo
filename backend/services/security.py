"""Security utilities: Encryption service using AES-256 (Fernet)."""

import base64
import hashlib
import os
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken


class EncryptionService:
    _instance: Optional["EncryptionService"] = None
    _fernet: Optional[Fernet] = None

    def __new__(cls) -> "EncryptionService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        key = self._derive_key(os.getenv("ENCRYPTION_KEY", "change-me"))
        self._fernet = Fernet(key)

    @staticmethod
    def _derive_key(secret: str) -> bytes:
        key_bytes = hashlib.sha256(secret.encode()).digest()
        return base64.urlsafe_b64encode(key_bytes)

    def encrypt(self, plaintext: str) -> str:
        if self._fernet is None:
            raise RuntimeError("Encryption service not initialized")
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        if self._fernet is None:
            raise RuntimeError("Encryption service not initialized")
        try:
            return self._fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        except InvalidToken as e:
            raise ValueError("Invalid or corrupted encrypted data") from e


def get_encryption_service() -> EncryptionService:
    return EncryptionService()
