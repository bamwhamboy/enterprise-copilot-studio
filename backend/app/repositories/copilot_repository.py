"""Repository for the Copilot entity."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.copilot import Copilot
from app.repositories.base import BaseRepository


class CopilotRepository(BaseRepository[Copilot]):
    model = Copilot

    async def get(self, id: uuid.UUID) -> Copilot | None:
        stmt = (
            select(Copilot)
            .where(Copilot.id == id)
            .options(selectinload(Copilot.knowledge_sources))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(
        self, *, offset: int = 0, limit: int = 100, organization_id: uuid.UUID | None = None
    ) -> list[Copilot]:
        stmt = (
            select(Copilot)
            .options(selectinload(Copilot.knowledge_sources))
            .order_by(Copilot.created_at.desc())
        )
        if organization_id is not None:
            stmt = stmt.where(Copilot.organization_id == organization_id)
        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
