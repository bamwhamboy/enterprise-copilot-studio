"""Repository for the Document entity."""

import uuid

from sqlalchemy import select

from app.models.document import Document
from app.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    model = Document

    async def list_all(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        knowledge_source_id: uuid.UUID | None = None,
    ) -> list[Document]:
        stmt = select(Document).order_by(Document.created_at.desc())
        if knowledge_source_id is not None:
            stmt = stmt.where(Document.knowledge_source_id == knowledge_source_id)
        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
