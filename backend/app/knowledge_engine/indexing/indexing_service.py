"""Indexing service.

Orchestrates the "when a document has been successfully parsed" flow:
read its extracted text -> hierarchical chunking -> embed + store each
chunk in Qdrant -> update the Document row's chunk/embedding counts and
``index_status`` in Postgres.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from llama_index.core import StorageContext, VectorStoreIndex
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.schema import TextNode
from llama_index.vector_stores.qdrant import QdrantVectorStore
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.knowledge_engine.chunking.hierarchical_chunker import HierarchicalChunker
from app.knowledge_engine.models import HierarchicalChunk
from app.repositories.document_repository import DocumentRepository

logger = get_logger(__name__)


class DocumentNotReadyError(Exception):
    """Raised when indexing is attempted on a document not yet ingestion-READY."""

    def __init__(self, document_id: uuid.UUID, processing_status: str | None) -> None:
        self.document_id = document_id
        self.processing_status = processing_status
        super().__init__(
            f"Document {document_id} is not ready for indexing "
            f"(processing_status={processing_status!r}, expected 'READY')."
        )


def _chunk_to_node(chunk: HierarchicalChunk) -> TextNode:
    metadata: dict[str, Any] = chunk.metadata.model_dump(mode="json")
    # LlamaIndex's node_to_metadata_dict (used when writing to any vector
    # store) unconditionally overwrites a "document_id" key with
    # node.ref_doc_id (legacy Chroma/Pinecone/Qdrant compatibility code) —
    # our nodes have no ref_doc_id set, so that would silently clobber our
    # real document_id with the literal string "None". Renaming avoids the
    # collision entirely; see llama_index/core/vector_stores/utils.py.
    metadata["source_document_id"] = metadata.pop("document_id")
    return TextNode(text=chunk.text, id_=chunk.node_id, metadata=metadata)


class IndexingService:
    """Runs the chunk -> embed -> store -> status-update pipeline for one document."""

    def __init__(
        self,
        session: AsyncSession,
        chunker: HierarchicalChunker,
        embed_model: BaseEmbedding,
        vector_store: QdrantVectorStore,
    ) -> None:
        self.session = session
        self.repository = DocumentRepository(session)
        self.chunker = chunker
        self.embed_model = embed_model
        self.vector_store = vector_store

    async def index_document(self, document_id: uuid.UUID) -> dict[str, Any]:
        document = await self.repository.get(document_id)
        if document is None:
            raise NotFoundError("Document", document_id)

        if document.processing_status != "READY" or not document.extracted_text_path:
            raise DocumentNotReadyError(document_id, document.processing_status)

        document.index_status = "INDEXING"
        await self.session.commit()
        logger.info("Document %s -> INDEXING", document_id)

        try:
            text = Path(document.extracted_text_path).read_text(encoding="utf-8")

            chunks = self.chunker.chunk(
                text=text,
                document_id=str(document.id),
                knowledge_source_id=str(document.knowledge_source_id),
                document_name=document.original_filename or document.name,
            )
            nodes = [_chunk_to_node(chunk) for chunk in chunks]

            storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
            VectorStoreIndex(
                nodes,
                storage_context=storage_context,
                embed_model=self.embed_model,
            )
        except Exception as exc:
            logger.error("Document %s failed to index: %s", document_id, exc)
            document.index_status = "FAILED"
            await self.session.commit()
            raise

        document.chunks = len(chunks)
        document.embeddings = len(chunks)
        document.index_status = "INDEXED"
        await self.session.commit()
        logger.info("Document %s -> INDEXED (%d chunks)", document_id, len(chunks))

        return {"document_id": str(document_id), "chunks_indexed": len(chunks)}
