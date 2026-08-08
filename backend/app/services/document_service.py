"""Service layer for Document."""

import uuid
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DocumentProcessingError, NotFoundError
from app.core.logging import get_logger
from app.knowledge_engine.pipeline.ingestion_pipeline import DocumentIngestionPipeline
from app.knowledge_engine.storage.document_storage import DocumentStorageService
from app.models.document import Document
from app.repositories.document_repository import DocumentRepository
from app.repositories.knowledge_source_repository import KnowledgeSourceRepository
from app.schemas.document import DocumentCreate

logger = get_logger(__name__)


class DocumentService:
    def __init__(
        self,
        session: AsyncSession,
        storage: DocumentStorageService,
        pipeline: DocumentIngestionPipeline,
    ) -> None:
        self.session = session
        self.repository = DocumentRepository(session)
        self.knowledge_source_repository = KnowledgeSourceRepository(session)
        self.storage = storage
        self.pipeline = pipeline

    async def list_documents(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        knowledge_source_id: uuid.UUID | None = None,
        organization_id: uuid.UUID | None = None,
    ) -> list[Document]:
        return await self.repository.list_all(
            offset=offset,
            limit=limit,
            knowledge_source_id=knowledge_source_id,
            organization_id=organization_id,
        )

    async def get_document(
        self, document_id: uuid.UUID, *, organization_id: uuid.UUID | None = None
    ) -> Document:
        document = await self.repository.get(document_id)
        if document is None:
            raise NotFoundError("Document", document_id)
        # Document has no organization_id of its own -- ownership is
        # checked via its parent KnowledgeSource (see that model's own
        # comment on why). Same 404-not-403 reasoning as
        # CopilotService.get_copilot.
        if (
            organization_id is not None
            and document.knowledge_source.organization_id != organization_id
        ):
            raise NotFoundError("Document", document_id)
        return document

    async def _get_owned_knowledge_source(
        self, knowledge_source_id: uuid.UUID, *, organization_id: uuid.UUID | None
    ):
        """Fetch the parent knowledge source, enforcing it belongs to the
        caller's organization before anything gets created/uploaded under
        it -- without this, a user could attach a document to another
        organization's knowledge source just by knowing its id.
        """
        parent = await self.knowledge_source_repository.get(knowledge_source_id)
        if parent is None:
            raise NotFoundError("KnowledgeSource", knowledge_source_id)
        if organization_id is not None and parent.organization_id != organization_id:
            raise NotFoundError("KnowledgeSource", knowledge_source_id)
        return parent

    async def create_document(
        self, payload: DocumentCreate, *, organization_id: uuid.UUID | None = None
    ) -> Document:
        await self._get_owned_knowledge_source(
            payload.knowledge_source_id, organization_id=organization_id
        )

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

    async def upload_document(
        self,
        *,
        knowledge_source_id: uuid.UUID,
        filename: str,
        content_type: str | None,
        content: bytes,
        organization_id: uuid.UUID | None = None,
    ) -> Document:
        """Ingest an uploaded PDF.

        Registers the document immediately as ``UPLOADED`` (so a row +
        file exist even if parsing later fails), then walks it through
        ``PROCESSING`` to ``READY`` or ``FAILED``, committing at each
        transition for an accurate, debuggable status history.
        """
        await self._get_owned_knowledge_source(
            knowledge_source_id, organization_id=organization_id
        )

        saved = await self.pipeline.save_upload(
            filename=filename, content_type=content_type, content=content
        )

        document = Document(
            knowledge_source_id=knowledge_source_id,
            name=filename,
            status="pending",
            original_filename=saved.file_metadata.original_filename,
            storage_path=str(saved.storage_path),
            mime_type=saved.file_metadata.mime_type,
            file_size_bytes=saved.file_metadata.file_size_bytes,
            processing_status="UPLOADED",
        )
        document = await self.repository.create(document)
        await self.session.commit()
        logger.info("Document %s registered as UPLOADED (%s)", document.id, filename)

        document.processing_status = "PROCESSING"
        await self.session.commit()
        logger.info("Document %s -> PROCESSING", document.id)

        try:
            parsed_upload = await self.pipeline.parse_and_store_text(Path(document.storage_path))
        except DocumentProcessingError as exc:
            logger.error("Document %s failed to process: %s", document.id, exc)
            document.processing_status = "FAILED"
            await self.session.commit()
            raise

        document.pages = parsed_upload.parsed.page_count
        document.extracted_text_path = str(parsed_upload.extracted_text_path)
        document.processing_status = "READY"
        document.status = "indexed"  # keep Sprint 2's coarse status field in sync
        await self.session.commit()
        logger.info(
            "Document %s -> READY (%d pages, %d chars extracted)",
            document.id,
            parsed_upload.parsed.page_count,
            len(parsed_upload.parsed.text),
        )

        return document

    async def delete_document(
        self, document_id: uuid.UUID, *, organization_id: uuid.UUID | None = None
    ) -> None:
        document = await self.get_document(document_id, organization_id=organization_id)
        self.storage.delete(document.storage_path)
        self.storage.delete(document.extracted_text_path)
        await self.repository.delete(document)
        await self.session.commit()
        logger.info("Document %s deleted (files cleaned up)", document_id)
