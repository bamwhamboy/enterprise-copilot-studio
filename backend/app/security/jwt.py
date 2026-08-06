"""JWT access/refresh token creation and verification.

Access tokens are short-lived and stateless (no DB lookup needed to
verify one). Refresh tokens are long-lived and *are* checked against
the database (app/repositories/refresh_token_repository.py) so they
can be revoked -- a bare JWT can't be revoked before its expiry, which
is why logout/rotation needs a server-side record of valid ones.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal, TypedDict

import jwt

from app.core.config import Settings

TokenType = Literal["access", "refresh"]


class TokenPayload(TypedDict):
    sub: str  # user id, as a string
    type: TokenType
    exp: int  # Unix timestamp
    jti: str  # unique token id -- refresh tokens are looked up/revoked by this


class InvalidTokenError(Exception):
    """Raised when a token is malformed, expired, or of the wrong type."""


def _encode(
    user_id: uuid.UUID, token_type: TokenType, expires_at: datetime, settings: Settings
) -> tuple[str, str]:
    jti = str(uuid.uuid4())
    payload = {"sub": str(user_id), "type": token_type, "exp": expires_at, "jti": jti}
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, jti


def create_access_token(user_id: uuid.UUID, settings: Settings) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    token, _ = _encode(user_id, "access", expires_at, settings)
    return token


def create_refresh_token(user_id: uuid.UUID, settings: Settings) -> tuple[str, str, datetime]:
    """Returns ``(raw_token, jti, expires_at)``.

    The raw token is returned to the client; the caller (AuthService)
    persists a SHA-256 hash of it via RefreshTokenRepository -- never
    the raw value.
    """
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    token, jti = _encode(user_id, "refresh", expires_at, settings)
    return token, jti, expires_at


def decode_token(token: str, settings: Settings, *, expected_type: TokenType) -> TokenPayload:
    """Decode and validate a token, including its expected type.

    Raises InvalidTokenError for any failure -- expired, malformed,
    bad signature, or wrong type -- so callers have one exception to
    handle regardless of cause.
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise InvalidTokenError("Token has expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise InvalidTokenError("Token is invalid.") from exc

    if payload.get("type") != expected_type:
        raise InvalidTokenError(f"Expected a '{expected_type}' token.")

    return payload  # type: ignore[return-value]
