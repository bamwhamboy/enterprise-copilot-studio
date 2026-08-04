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
from app.services.copilot_service import CopilotService
from app.services.document_service import DocumentService
from app.services.knowledge_source_service import KnowledgeSourceService

SettingsDep = Annotated[Settings, Depends(get_settings)]


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Alias around ``app.database.session.get_db`` for a stable import path."""
    async for session in get_db():
        yield session


DbSessionDep = Annotated[AsyncSession, Depends(get_db_session)]


async def get_copilot_service(session: DbSessionDep) -> CopilotService:
    return CopilotService(session)


async def get_knowledge_source_service(session: DbSessionDep) -> KnowledgeSourceService:
    return KnowledgeSourceService(session)


async def get_document_service(session: DbSessionDep) -> DocumentService:
    return DocumentService(session)


CopilotServiceDep = Annotated[CopilotService, Depends(get_copilot_service)]
KnowledgeSourceServiceDep = Annotated[KnowledgeSourceService, Depends(get_knowledge_source_service)]
DocumentServiceDep = Annotated[DocumentService, Depends(get_document_service)]
