"""Repository for the Document entity."""

import uuid

from sqlalchemy import select, update

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

    async def reset_stale_indexing(self) -> int:
        """Reset any document stuck at index_status="INDEXING" back to "FAILED".

        Indexing runs synchronously inside the request handler for
        POST /index/{id} -- there is no background worker or queue that
        could legitimately still be "in progress" after a process
        restart. Any document found in this state at startup is
        unambiguously a leftover from a process that died mid-index
        (e.g. an out-of-memory kill while loading the embedding model,
        which bypasses Python's own exception handling entirely and so
        never reaches the code that would normally mark it FAILED).
        Without this, such a document is stuck forever: index_status
        never becomes "FAILED", so the frontend's retry control (which
        only appears for NOT_INDEXED/FAILED) never has anything to
        retry.
        """
        stmt = (
            update(Document)
            .where(Document.index_status == "INDEXING")
            .values(index_status="FAILED")
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount or 0
