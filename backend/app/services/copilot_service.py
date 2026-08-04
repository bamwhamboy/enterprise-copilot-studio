"""Service layer for Copilot.

Routers depend on this, never on the repository or session directly.
This is where relationship wiring (attaching knowledge sources) and
not-found handling live, kept separate from both HTTP concerns and raw
persistence.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.copilot import Copilot
from app.repositories.copilot_repository import CopilotRepository
from app.repositories.knowledge_source_repository import KnowledgeSourceRepository
from app.schemas.copilot import CopilotCreate, CopilotUpdate


class CopilotService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = CopilotRepository(session)
        self.knowledge_source_repository = KnowledgeSourceRepository(session)

    async def list_copilots(self, *, offset: int = 0, limit: int = 100) -> list[Copilot]:
        return await self.repository.list_all(offset=offset, limit=limit)

    async def get_copilot(self, copilot_id: uuid.UUID) -> Copilot:
        copilot = await self.repository.get(copilot_id)
        if copilot is None:
            raise NotFoundError("Copilot", copilot_id)
        return copilot

    async def create_copilot(self, payload: CopilotCreate) -> Copilot:
        knowledge_sources = await self.knowledge_source_repository.get_many(
            payload.knowledge_source_ids
        )

        copilot = Copilot(
            name=payload.name,
            description=payload.description,
            domain=payload.domain,
            status=payload.status,
            model=payload.model,
            knowledge_sources=knowledge_sources,
        )
        copilot = await self.repository.create(copilot)
        await self.session.commit()
        return await self.get_copilot(copilot.id)

    async def update_copilot(self, copilot_id: uuid.UUID, payload: CopilotUpdate) -> Copilot:
        copilot = await self.get_copilot(copilot_id)

        update_data = payload.model_dump(exclude_unset=True, exclude={"knowledge_source_ids"})
        for field, value in update_data.items():
            setattr(copilot, field, value)

        if payload.knowledge_source_ids is not None:
            copilot.knowledge_sources = await self.knowledge_source_repository.get_many(
                payload.knowledge_source_ids
            )

        await self.session.commit()
        return await self.get_copilot(copilot_id)

    async def delete_copilot(self, copilot_id: uuid.UUID) -> None:
        copilot = await self.get_copilot(copilot_id)
        await self.repository.delete(copilot)
        await self.session.commit()
