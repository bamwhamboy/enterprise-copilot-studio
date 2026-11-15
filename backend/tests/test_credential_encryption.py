import pytest
from cryptography.fernet import Fernet

from app.core.config import get_settings
from app.security.credential_encryption import (
    decrypt_credential,
    encrypt_credential,
)


def test_encrypt_decrypt_round_trip(monkeypatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setattr(
        get_settings(), "GITHUB_TOKEN_ENCRYPTION_KEY", key
    )
    token = "github_pat_test_secret_123"
    encrypted = encrypt_credential(token)

    assert encrypted != token
    assert decrypt_credential(encrypted) == token


def test_empty_credential_rejected():
    with pytest.raises(ValueError, match="must not be empty"):
        encrypt_credential("")


def test_invalid_ciphertext_rejected(monkeypatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setattr(
        get_settings(), "GITHUB_TOKEN_ENCRYPTION_KEY", key
    )
    with pytest.raises(ValueError, match="cannot be decrypted"):
        decrypt_credential("not-valid-ciphertext")


def test_missing_key_fails_closed(monkeypatch):
    monkeypatch.setattr(
        get_settings(), "GITHUB_TOKEN_ENCRYPTION_KEY", None
    )
    with pytest.raises(RuntimeError, match="must be configured"):
        encrypt_credential("github_pat_test_secret_123")
