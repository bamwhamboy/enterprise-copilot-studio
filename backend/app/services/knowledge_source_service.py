"""Service layer for KnowledgeSource."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.knowledge_source import KnowledgeSource
from app.repositories.knowledge_source_repository import KnowledgeSourceRepository
from app.schemas.knowledge_source import KnowledgeSourceCreate, KnowledgeSourceUpdate


class KnowledgeSourceService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = KnowledgeSourceRepository(session)

    async def list_knowledge_sources(
        self, *, offset: int = 0, limit: int = 100
    ) -> list[KnowledgeSource]:
        return await self.repository.list_all(offset=offset, limit=limit)

    async def get_knowledge_source(self, knowledge_source_id: uuid.UUID) -> KnowledgeSource:
        knowledge_source = await self.repository.get(knowledge_source_id)
        if knowledge_source is None:
            raise NotFoundError("KnowledgeSource", knowledge_source_id)
        return knowledge_source

    async def create_knowledge_source(
        self, payload: KnowledgeSourceCreate
    ) -> KnowledgeSource:
        knowledge_source = KnowledgeSource(
            name=payload.name,
            source_type=payload.source_type,
            status=payload.status,
        )
        knowledge_source = await self.repository.create(knowledge_source)
        await self.session.commit()
        return await self.get_knowledge_source(knowledge_source.id)

    async def update_knowledge_source(
        self, knowledge_source_id: uuid.UUID, payload: KnowledgeSourceUpdate
    ) -> KnowledgeSource:
        knowledge_source = await self.get_knowledge_source(knowledge_source_id)

        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(knowledge_source, field, value)

        await self.session.commit()
        return await self.get_knowledge_source(knowledge_source_id)

    async def delete_knowledge_source(self, knowledge_source_id: uuid.UUID) -> None:
        knowledge_source = await self.get_knowledge_source(knowledge_source_id)
        await self.repository.delete(knowledge_source)
        await self.session.commit()
