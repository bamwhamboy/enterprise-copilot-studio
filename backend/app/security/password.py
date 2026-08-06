"""Password hashing and verification.

Uses the ``bcrypt`` library directly rather than passlib -- fewer
moving parts, actively maintained, and this is all bcrypt itself does
under the hood anyway.
"""

import bcrypt

_BCRYPT_MAX_BYTES = 72  # bcrypt silently truncates beyond this; validated up front instead.


def hash_password(password: str) -> str:
    """Hash a plaintext password for storage."""
    if len(password.encode("utf-8")) > _BCRYPT_MAX_BYTES:
        raise ValueError(f"Password must be at most {_BCRYPT_MAX_BYTES} bytes.")
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))
    except ValueError:
        # Malformed hash in storage -- treat as a verification failure,
        # never raise out of an auth check.
        return False
