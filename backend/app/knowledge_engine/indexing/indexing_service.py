"""Indexing service.

Orchestrates the "when a document has been successfully parsed" flow:
read its extracted text -> hierarchical chunking -> embed + store each
chunk in Qdrant -> update the Document row's chunk/embedding counts and
``index_status`` in Postgres.

Also (additively, since Graph RAG) runs graph extraction against the
same hierarchical chunks once they exist, before the vector/embedding
step -- see ``index_document`` for exactly where and why. Graph
extraction is entirely independent of the vector path: it reuses the
chunks already produced by ``self.chunker``, never re-reads the
document or re-chunks it, and a graph extraction failure (partial or
total) can never fail the document's indexing or change
``index_status`` away from what vector indexing alone would have set.
"""

from __future__ import annotations

import asyncio
import gc
import time
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.schema import MetadataMode, TextNode
from llama_index.vector_stores.qdrant import QdrantVectorStore
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.knowledge_engine.chunking.hierarchical_chunker import HierarchicalChunker
from app.knowledge_engine.models import HierarchicalChunk
from app.repositories.document_repository import DocumentRepository

# Deferred to TYPE_CHECKING only -- app.knowledge_engine.graph.graph_extraction_service
# imports app.knowledge_engine.graph.extractor, which imports LLMGateway/litellm.
# See app/core/dependencies.py's get_graph_extraction_service for why that cost
# must only be paid when graph extraction is actually enabled, not merely by
# importing this module (which happens unconditionally at app startup).
if TYPE_CHECKING:
    from app.knowledge_engine.graph.graph_extraction_service import GraphExtractionService

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


def _embed_nodes(nodes: list[TextNode], embed_model: BaseEmbedding) -> None:
    """Embed every node in place (sets ``node.embedding``).

    Plain, synchronous entry point -- kept as a standalone module-level
    function (rather than called inline) specifically so it has a single,
    unambiguous call site to hand to ``asyncio.to_thread`` below, and so
    it's separately timeable from the Qdrant write step in
    ``index_document``. Equivalent to what ``VectorStoreIndex(nodes, ...)``
    does internally before its own vector-store ``add`` call -- split out
    here purely so embedding time and Qdrant-write time can be measured
    independently; the embeddings produced and the batching behavior
    (``embed_model.embed_batch_size``) are unchanged either way.
    """
    embeddings = embed_model.get_text_embedding_batch(
        [node.get_content(metadata_mode=MetadataMode.EMBED) for node in nodes]
    )
    for node, embedding in zip(nodes, embeddings):
        node.embedding = embedding


def _write_nodes_to_vector_store(
    nodes: list[TextNode], vector_store: QdrantVectorStore
) -> list[str]:
    """Plain, synchronous entry point for the Qdrant write step -- same
    reasoning as ``_embed_nodes`` above. Requires every node to already
    have an embedding set (``_embed_nodes`` must run first).
    """
    return vector_store.add(nodes)


class IndexingService:
    """Runs the chunk -> embed -> store -> status-update pipeline for one document."""

    def __init__(
        self,
        session: AsyncSession,
        chunker: HierarchicalChunker,
        embed_model: BaseEmbedding,
        vector_store: QdrantVectorStore,
        graph_extraction_service: GraphExtractionService | None = None,
    ) -> None:
        self.session = session
        self.repository = DocumentRepository(session)
        self.chunker = chunker
        self.embed_model = embed_model
        self.vector_store = vector_store
        # Optional and additive -- None (the default) means graph
        # extraction is skipped entirely, and vector indexing is
        # completely unaffected either way. See app/core/dependencies.py
        # for how/when this actually gets constructed (gated behind
        # settings.GRAPH_EXTRACTION_ENABLED).
        self.graph_extraction_service = graph_extraction_service

    async def index_document(self, document_id: uuid.UUID) -> dict[str, Any]:
        document = await self.repository.get(document_id)
        if document is None:
            raise NotFoundError("Document", document_id)

        if document.processing_status != "READY" or not document.extracted_text_path:
            raise DocumentNotReadyError(document_id, document.processing_status)

        document.index_status = "INDEXING"
        await self.session.commit()
        logger.info("Document %s -> INDEXING", document_id)

        # Lightweight wall-clock timing instrumentation only -- no behavior
        # change. Each stage's duration is measured around the exact same
        # calls that already existed (chunking) or that replace a single
        # fused call with the same work split into two explicit,
        # separately-timed steps (embedding, Qdrant write -- see
        # _embed_nodes/_write_nodes_to_vector_store above). Reported
        # together in one summary log line once indexing succeeds.
        pipeline_start = time.perf_counter()

        try:
            text = Path(document.extracted_text_path).read_text(encoding="utf-8")

            try:
                chunking_start = time.perf_counter()
                # asyncio.to_thread: chunking is synchronous, CPU-bound
                # work (tiktoken tokenization across up to 3 hierarchical
                # levels) that previously ran directly on the event loop,
                # blocking it -- including blocking this same process's
                # ability to answer Render's own health check request to
                # /health, which has zero real dependencies and would
                # otherwise respond instantly -- for the entire duration.
                # A health-check timeout during that blocked window
                # produces a forceful restart that's indistinguishable
                # from an OOM kill by exit code alone (both are 137).
                chunks = await asyncio.to_thread(
                    self.chunker.chunk,
                    text=text,
                    document_id=str(document.id),
                    knowledge_source_id=str(document.knowledge_source_id),
                    document_name=document.original_filename or document.name,
                )
            except Exception:
                logger.exception("Document %s failed during chunking", document_id)
                raise
            chunking_duration = time.perf_counter() - chunking_start

            # Graph RAG extraction runs here deliberately: chunks exist
            # (just produced above) but haven't been released yet (that
            # happens a few lines below, via `del text, chunks`), and
            # vector indexing hasn't started. This is purely additive --
            # see _run_graph_extraction's docstring for why nothing it
            # does can affect vector indexing's outcome or this
            # document's index_status.
            graph_extraction_summary: dict[str, Any] = (
                await self._run_graph_extraction(document.id, chunks)
                if self.graph_extraction_service is not None
                else {"status": "skipped"}
            )

            # The raw extracted text and the HierarchicalChunk objects are
            # both fully redundant the moment TextNodes are built from them
            # (each TextNode holds its own copy of the same chunk text) --
            # for hierarchical chunking specifically, the total text volume
            # across all chunks combined can be several times the original
            # document's length, since the same content is deliberately
            # duplicated at each granularity level (Document/Section/
            # Paragraph). Capturing the count and releasing both before the
            # memory-intensive embedding step below, rather than leaving
            # them for Python's own GC timing, matters on a tight memory
            # budget.
            chunk_count = len(chunks)
            nodes = [_chunk_to_node(chunk) for chunk in chunks]
            del text, chunks
            gc.collect()

            try:
                # Same reasoning as the chunking step above -- ONNX
                # Runtime inference across every chunk (and, on the very
                # first indexing request in the process's lifetime, the
                # one-time embedding model download+load happening
                # underneath it) is the single longest CPU-bound stretch
                # in this whole pipeline, and the one most likely to
                # exceed a health-check timeout if left blocking the
                # event loop. Both ONNX Runtime's native inference and
                # tiktoken's Rust tokenizer release the GIL during their
                # actual computation, which is what makes offloading to a
                # thread (not just moving the same blocking problem
                # elsewhere) genuinely effective here.
                embedding_start = time.perf_counter()
                await asyncio.to_thread(_embed_nodes, nodes, self.embed_model)
                embedding_duration = time.perf_counter() - embedding_start

                qdrant_start = time.perf_counter()
                written_ids = await asyncio.to_thread(
                    _write_nodes_to_vector_store, nodes, self.vector_store
                )
                qdrant_duration = time.perf_counter() - qdrant_start
            except Exception:
                logger.exception(
                    "Document %s failed while embedding/storing %d chunk(s) "
                    "(this is the embed-and-write-to-Qdrant step, distinct "
                    "from loading the embedding model itself, which -- if "
                    "that's where this actually failed -- would have logged "
                    "separately from app.knowledge_engine.embeddings.embedding_model)",
                    document_id,
                    len(nodes),
                )
                raise
        except Exception:
            # logger.exception (not logger.error) so the full traceback
            # reaches the logs, not just str(exc) -- a bare exception
            # message alone was previously the only thing recorded here,
            # which usually isn't enough to actually diagnose what failed.
            logger.exception("Document %s failed to index", document_id)
            document.index_status = "FAILED"
            await self.session.commit()
            raise

        document.chunks = chunk_count
        document.embeddings = chunk_count
        document.index_status = "INDEXED"
        await self.session.commit()
        pipeline_duration = time.perf_counter() - pipeline_start
        logger.info(
            "Document %s -> INDEXED (%d chunks) | timing: total=%.3fs "
            "chunking=%.3fs (%d chunks) embedding=%.3fs (batch_size=%d) "
            "qdrant_write=%.3fs (%d vectors written)",
            document_id,
            chunk_count,
            pipeline_duration,
            chunking_duration,
            chunk_count,
            embedding_duration,
            self.embed_model.embed_batch_size,
            qdrant_duration,
            len(written_ids),
        )

        return {
            "document_id": str(document_id),
            "chunks_indexed": chunk_count,
            "graph_extraction": graph_extraction_summary,
        }

    async def _run_graph_extraction(
        self, document_id: uuid.UUID, chunks: list[HierarchicalChunk]
    ) -> dict[str, Any]:
        """Runs Graph RAG extraction against the exact same chunks vector
        indexing is about to use, and returns a summary dict -- but never
        lets a graph extraction failure propagate out of this method.

        ``GraphExtractionService.extract_for_document`` already isolates
        per-chunk failures internally (one bad chunk's LLM/DB error
        doesn't stop the rest of the document's graph extraction). This
        try/except is the *outer* safety net, for anything that could go
        wrong outside that per-chunk loop -- so regardless of what
        breaks here, vector indexing is guaranteed to run immediately
        after this returns, and this document's ``index_status`` is
        never affected by graph extraction's outcome.
        """
        try:
            result = await self.graph_extraction_service.extract_for_document(
                document_id, chunks
            )
        except Exception:
            logger.exception(
                "Document %s: graph extraction failed entirely; continuing "
                "with vector indexing",
                document_id,
            )
            return {
                "status": "failed",
                "error": "graph extraction raised an unexpected error",
            }

        if result.chunks_failed:
            logger.warning(
                "Document %s: graph extraction completed with %d/%d chunk "
                "failure(s): %s",
                document_id,
                result.chunks_failed,
                result.chunks_processed,
                [error.chunk_id for error in result.errors],
            )
            status = "partial" if result.chunks_succeeded else "failed"
        else:
            logger.info(
                "Document %s: graph extraction complete (%d entities, %d "
                "relationships, %d evidence, %d chunks)",
                document_id,
                result.entities_created,
                result.relationships_created,
                result.evidence_created,
                result.chunks_processed,
            )
            status = "completed"

        return {
            "status": status,
            "chunks_processed": result.chunks_processed,
            "chunks_succeeded": result.chunks_succeeded,
            "chunks_failed": result.chunks_failed,
            "entities_created": result.entities_created,
            "relationships_created": result.relationships_created,
            "evidence_created": result.evidence_created,
        }
