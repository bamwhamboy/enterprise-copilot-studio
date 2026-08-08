"""FastAPI authentication/authorization dependencies.

Self-contained -- uses app.database.session.get_db directly rather than
app.core.dependencies, to avoid a circular import: app.core.dependencies
imports *from* this module to build the DI aliases routers use.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.database.session import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.security.jwt import InvalidTokenError, decode_token

# tokenUrl points Swagger's "Authorize" button at the real login endpoint
# (settings.API_V1_PREFIX + "/auth/login") so Bearer auth works in /docs
# out of the box.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    settings: Annotated[Settings, Depends(get_settings)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token, settings, expected_type="access")
    except InvalidTokenError:
        raise credentials_exception

    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError):
        raise credentials_exception

    user = await UserRepository(session).get(user_id)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(user: Annotated[User, Depends(get_current_user)]) -> User:
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user account."
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_active_user)]


def scoped_organization_id(user: User) -> uuid.UUID | None:
    """The organization a tenant-scoped query should filter by for this user.

    Returns ``None`` for super_admin (see every organization's data,
    matching the existing precedent in api/v1/organizations.py's own
    "all, for super_admin; otherwise just your own" listing), otherwise
    the user's own organization_id. Centralized here so every router
    that needs tenant scoping (copilots, knowledge sources, documents)
    applies the exact same rule rather than each re-deriving it slightly
    differently.
    """
    from app.models.role import SUPER_ADMIN

    return None if user.role.name == SUPER_ADMIN else user.organization_id


def require_role(*role_names: str) -> Callable[[User], User]:
    """Dependency factory: only allow users whose role name is in role_names.

    Usage: ``Depends(require_role(SUPER_ADMIN, ORGANIZATION_ADMIN))``.
    """

    async def _check(user: CurrentUser) -> User:
        if user.role.name not in role_names:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of these roles: {', '.join(role_names)}.",
            )
        return user

    return _check
