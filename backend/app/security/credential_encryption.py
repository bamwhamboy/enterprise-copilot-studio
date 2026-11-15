"""Encryption helpers for external connector credentials."""

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings


def _fernet() -> Fernet:
    key = get_settings().GITHUB_TOKEN_ENCRYPTION_KEY
    if not key:
        raise RuntimeError(
            "GITHUB_TOKEN_ENCRYPTION_KEY must be configured to store connector credentials."
        )
    try:
        return Fernet(key.encode("utf-8"))
    except (ValueError, TypeError) as exc:
        raise RuntimeError("GITHUB_TOKEN_ENCRYPTION_KEY is invalid.") from exc


def encrypt_credential(value: str) -> str:
    """Encrypt a credential before persistence."""
    if not value:
        raise ValueError("Credential must not be empty.")
    return _fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_credential(encrypted_value: str) -> str:
    """Decrypt a previously encrypted credential."""
    try:
        return _fernet().decrypt(encrypted_value.encode("utf-8")).decode("utf-8")
    except (InvalidToken, UnicodeDecodeError) as exc:
        raise ValueError("Credential cannot be decrypted with the configured key.") from exc
