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

    async def list_copilots(
        self, *, offset: int = 0, limit: int = 100, organization_id: uuid.UUID | None = None
    ) -> list[Copilot]:
        return await self.repository.list_all(
            offset=offset, limit=limit, organization_id=organization_id
        )

    async def get_copilot(
        self, copilot_id: uuid.UUID, *, organization_id: uuid.UUID | None = None
    ) -> Copilot:
        copilot = await self.repository.get(copilot_id)
        if copilot is None:
            raise NotFoundError("Copilot", copilot_id)
        # organization_id=None means an unscoped caller (super_admin) --
        # otherwise, a copilot belonging to a different organization is
        # treated identically to a nonexistent one (404, not 403) so a
        # caller can't distinguish "doesn't exist" from "exists but isn't
        # yours" by probing IDs.
        if organization_id is not None and copilot.organization_id != organization_id:
            raise NotFoundError("Copilot", copilot_id)
        return copilot

    async def create_copilot(
        self, payload: CopilotCreate, *, organization_id: uuid.UUID
    ) -> Copilot:
        knowledge_sources = await self.knowledge_source_repository.get_many(
            payload.knowledge_source_ids, organization_id=organization_id
        )

        copilot = Copilot(
            name=payload.name,
            description=payload.description,
            domain=payload.domain,
            status=payload.status,
            model=payload.model,
            knowledge_sources=knowledge_sources,
            organization_id=organization_id,
        )
        copilot = await self.repository.create(copilot)
        await self.session.commit()
        return await self.get_copilot(copilot.id, organization_id=organization_id)

    async def update_copilot(
        self,
        copilot_id: uuid.UUID,
        payload: CopilotUpdate,
        *,
        organization_id: uuid.UUID | None = None,
    ) -> Copilot:
        copilot = await self.get_copilot(copilot_id, organization_id=organization_id)

        update_data = payload.model_dump(exclude_unset=True, exclude={"knowledge_source_ids"})
        for field, value in update_data.items():
            setattr(copilot, field, value)

        if payload.knowledge_source_ids is not None:
            copilot.knowledge_sources = await self.knowledge_source_repository.get_many(
                payload.knowledge_source_ids, organization_id=organization_id
            )

        await self.session.commit()
        return await self.get_copilot(copilot_id, organization_id=organization_id)

    async def delete_copilot(
        self, copilot_id: uuid.UUID, *, organization_id: uuid.UUID | None = None
    ) -> None:
        copilot = await self.get_copilot(copilot_id, organization_id=organization_id)
        await self.repository.delete(copilot)
        await self.session.commit()
