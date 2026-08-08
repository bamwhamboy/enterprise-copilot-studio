"""Repository for the KnowledgeSource entity."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.knowledge_source import KnowledgeSource
from app.repositories.base import BaseRepository


class KnowledgeSourceRepository(BaseRepository[KnowledgeSource]):
    model = KnowledgeSource

    async def get(self, id: uuid.UUID) -> KnowledgeSource | None:
        stmt = (
            select(KnowledgeSource)
            .where(KnowledgeSource.id == id)
            .options(selectinload(KnowledgeSource.documents))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(
        self, *, offset: int = 0, limit: int = 100, organization_id: uuid.UUID | None = None
    ) -> list[KnowledgeSource]:
        stmt = (
            select(KnowledgeSource)
            .options(selectinload(KnowledgeSource.documents))
            .order_by(KnowledgeSource.created_at.desc())
        )
        if organization_id is not None:
            stmt = stmt.where(KnowledgeSource.organization_id == organization_id)
        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_many(
        self, ids: list[uuid.UUID], *, organization_id: uuid.UUID | None = None
    ) -> list[KnowledgeSource]:
        """Fetch multiple knowledge sources by id (used when attaching to a Copilot).

        Silently drops any id belonging to a different organization
        (when organization_id is given) rather than erroring -- the
        caller only ever passes ids the user picked from their own,
        already-scoped list_knowledge_sources() results, so this is a
        defense against a spoofed id, not something a normal user
        should ever actually hit.
        """
        if not ids:
            return []
        stmt = select(KnowledgeSource).where(KnowledgeSource.id.in_(ids))
        if organization_id is not None:
            stmt = stmt.where(KnowledgeSource.organization_id == organization_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
