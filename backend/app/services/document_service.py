"""Service layer for Document."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.document import Document
from app.repositories.document_repository import DocumentRepository
from app.repositories.knowledge_source_repository import KnowledgeSourceRepository
from app.schemas.document import DocumentCreate


class DocumentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = DocumentRepository(session)
        self.knowledge_source_repository = KnowledgeSourceRepository(session)

    async def list_documents(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        knowledge_source_id: uuid.UUID | None = None,
    ) -> list[Document]:
        return await self.repository.list_all(
            offset=offset, limit=limit, knowledge_source_id=knowledge_source_id
        )

    async def get_document(self, document_id: uuid.UUID) -> Document:
        document = await self.repository.get(document_id)
        if document is None:
            raise NotFoundError("Document", document_id)
        return document

    async def create_document(self, payload: DocumentCreate) -> Document:
        # Confirm the parent knowledge source exists before creating a
        # document under it — a clearer 404 than a raw FK violation.
        parent = await self.knowledge_source_repository.get(payload.knowledge_source_id)
        if parent is None:
            raise NotFoundError("KnowledgeSource", payload.knowledge_source_id)

        document = Document(
            knowledge_source_id=payload.knowledge_source_id,
            name=payload.name,
            status=payload.status,
            pages=payload.pages,
            chunks=payload.chunks,
            embeddings=payload.embeddings,
        )
        document = await self.repository.create(document)
        await self.session.commit()
        return document

    async def delete_document(self, document_id: uuid.UUID) -> None:
        document = await self.get_document(document_id)
        await self.repository.delete(document)
        await self.session.commit()
