"""Auth service.

Orchestrates registration, login, refresh-token rotation, and logout.
Password hashing and JWT creation/verification live in app/security/;
this service composes them with persistence (via the repositories).
"""

from __future__ import annotations

import hashlib
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.logging import get_logger
from app.models.organization import Organization
from app.models.refresh_token import RefreshToken
from app.models.role import END_USER, ORGANIZATION_ADMIN
from app.models.user import User
from app.repositories.organization_repository import OrganizationRepository, RoleRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import TokenResponse, UserRegister
from app.security.jwt import InvalidTokenError, create_access_token, create_refresh_token, decode_token
from app.security.password import hash_password, verify_password

logger = get_logger(__name__)


class AuthenticationError(Exception):
    """Raised for invalid credentials, inactive users, or invalid/revoked tokens."""


def _hash_token(raw_token: str) -> str:
    """SHA-256 the raw refresh token for storage/lookup.

    Not bcrypt: this is a high-entropy random token used as a lookup
    key, not a low-entropy user-chosen secret -- a fast, deterministic
    hash is correct here (bcrypt's slow, salted design solves a
    different problem: brute-forcing weak passwords).
    """
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


class AuthService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self._settings = settings
        self.users = UserRepository(session)
        self.organizations = OrganizationRepository(session)
        self.roles = RoleRepository(session)
        self.refresh_tokens = RefreshTokenRepository(session)

    async def register(self, payload: UserRegister) -> User:
        existing = await self.users.get_by_email(payload.email)
        if existing is not None:
            raise AuthenticationError("An account with this email already exists.")

        organization = await self.organizations.get_by_name(payload.organization_name)
        role_name = END_USER
        if organization is None:
            organization = await self.organizations.create(
                Organization(name=payload.organization_name)
            )
            role_name = ORGANIZATION_ADMIN  # first user of a new org administers it

        role = await self.roles.get_by_name(role_name)
        # `role` is guaranteed non-None: the five roles are seeded by the
        # Sprint 6 migration and never deleted at the application layer.

        user = User(
            organization_id=organization.id,
            role_id=role.id,
            email=payload.email,
            hashed_password=hash_password(payload.password),
            full_name=payload.full_name,
        )
        user = await self.users.create(user)
        await self.session.commit()

        logger.info(
            "Registered user %s in organization %s (role=%s)",
            user.email,
            organization.name,
            role_name,
        )
        return await self.users.get(user.id)  # reload with organization/role eager-loaded

    async def authenticate(self, email: str, password: str) -> User:
        user = await self.users.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            raise AuthenticationError("Incorrect email or password.")
        if not user.is_active:
            raise AuthenticationError("This account has been deactivated.")
        return user

    async def issue_tokens(self, user: User) -> TokenResponse:
        access_token = create_access_token(user.id, self._settings)
        raw_refresh, _jti, expires_at = create_refresh_token(user.id, self._settings)

        token_record = RefreshToken(
            user_id=user.id, token_hash=_hash_token(raw_refresh), expires_at=expires_at
        )
        await self.refresh_tokens.create(token_record)
        await self.session.commit()

        return TokenResponse(
            access_token=access_token,
            refresh_token=raw_refresh,
            expires_in=self._settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def login(self, email: str, password: str) -> TokenResponse:
        user = await self.authenticate(email, password)
        logger.info("User %s logged in", user.email)
        return await self.issue_tokens(user)

    async def refresh(self, raw_refresh_token: str) -> TokenResponse:
        """Verify, rotate (revoke + reissue), and return new tokens.

        Rotation means a refresh token is single-use: reusing an
        already-rotated token (e.g. a stolen, replayed one) fails here,
        since it's already marked revoked.
        """
        try:
            payload = decode_token(raw_refresh_token, self._settings, expected_type="refresh")
        except InvalidTokenError as exc:
            raise AuthenticationError(str(exc)) from exc

        token_hash = _hash_token(raw_refresh_token)
        stored = await self.refresh_tokens.get_by_hash(token_hash)
        if stored is None or not self.refresh_tokens.is_valid(stored):
            raise AuthenticationError("Refresh token is invalid, expired, or has been revoked.")

        user = await self.users.get(uuid.UUID(payload["sub"]))
        if user is None or not user.is_active:
            raise AuthenticationError("Account is no longer active.")

        await self.refresh_tokens.revoke(stored)  # flushed; committed together with the reissue below
        return await self.issue_tokens(user)

    async def logout(self, raw_refresh_token: str) -> None:
        """Revoke the given refresh token. Idempotent: an unknown/already
        -revoked token is treated as "already logged out", not an error.
        """
        token_hash = _hash_token(raw_refresh_token)
        stored = await self.refresh_tokens.get_by_hash(token_hash)
        if stored is not None:
            await self.refresh_tokens.revoke(stored)
            await self.session.commit()
            logger.info("Refresh token revoked (user_id=%s)", stored.user_id)
