"""Reusable FastAPI dependencies.

Centralizing dependency providers here (rather than importing settings,
sessions, etc. ad hoc in each router) keeps ``Depends(...)`` usage
consistent and makes it trivial to override providers in tests via
``app.dependency_overrides``.
"""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.database.session import get_db

SettingsDep = Annotated[Settings, Depends(get_settings)]


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Alias around ``app.database.session.get_db`` for a stable import path."""
    async for session in get_db():
        yield session


DbSessionDep = Annotated[AsyncSession, Depends(get_db_session)]
