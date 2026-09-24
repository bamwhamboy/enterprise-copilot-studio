"""Retrieval node.

Runs (optionally) query rewriting, hybrid retrieval (Sprint 3B, reused
unchanged), (optionally) Graph RAG retrieval + fusion (Sprint 2,
config-gated per Settings.GRAPH_RAG_ENABLED, default off), and
(optionally) re-ranking + confidence scoring, all config-gated per
Settings.RAG_QUERY_REWRITE_ENABLED / Settings.RAG_RERANK_ENABLED.

Graph RAG integration point: MultiHopRetriever + GraphVectorFusion run
(unmodified) between hybrid retrieval and reranking. Fusion's output
(list[FusedResult]) is unwrapped to list[RetrievedChunk] via
`.chunk` before reranking/top-k/confidence/compression -- those four
components already operate on RetrievedChunk uniformly regardless of
whether a chunk came from vector retrieval or was synthesized from
graph evidence, so none of them need to change. See
graph_vector_fusion.py's own module docstring for why RetrievedChunk
was reused as the fusion output type in the first place.

Graph RAG is entirely fail-safe: disabled by default; skipped (not
errored) when no document_id/knowledge_source_id scope is available in
state (never performs an unrestricted graph query); and any exception
during graph retrieval/fusion is caught and logged, falling back to
the vector-only result for that request.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from app.agents.state import ChatState
from app.core.config import Settings
from app.core.logging import get_logger
from app.knowledge_engine.citations.citation_builder import build_retrieved_chunks
from app.knowledge_engine.compression.compression_service import ContextCompressionService
from app.knowledge_engine.models import RetrievedChunk
from app.knowledge_engine.retrieval.confidence_scorer import ConfidenceScorer
from app.knowledge_engine.retrieval.hybrid_retriever import HybridRetriever
from app.knowledge_engine.retrieval.query_rewriter import QueryRewriter
from app.knowledge_engine.retrieval.reranker import Reranker

# Deferred to TYPE_CHECKING only -- importing these for real pulls in
# app.knowledge_engine.graph.extractor, which imports LLMGateway/litellm
# (see app/core/dependencies.py's get_graph_extraction_service for the
# same reasoning). Actual imports happen inside _apply_graph_rag,
# gated behind settings.GRAPH_RAG_ENABLED.
if TYPE_CHECKING:
    from app.knowledge_engine.retrieval.graph_vector_fusion import GraphVectorFusion
    from app.knowledge_engine.retrieval.multi_hop_retriever import MultiHopRetriever

logger = get_logger(__name__)


def _parse_uuid(value: str | None) -> uuid.UUID | None:
    if not value:
        return None
    try:
        return uuid.UUID(value)
    except ValueError:
        logger.warning("Ignoring malformed UUID in chat state for graph scope: %r", value)
        return None


def make_retrieval_node(
    settings: Settings,
    retriever: HybridRetriever,
    compression: ContextCompressionService,
    *,
    # Injectable for tests only. Production callers should leave these
    # None -- see _apply_graph_rag, which lazily constructs the real
    # MultiHopRetriever/GraphVectorFusion (against a short-lived
    # session scoped to just that one read) only when
    # settings.GRAPH_RAG_ENABLED is True. Keeping this constructor's
    # signature otherwise unchanged means build_chat_workflow and
    # get_chat_workflow need no changes at all for this integration.
    graph_retriever: "MultiHopRetriever | None" = None,
    fusion: "GraphVectorFusion | None" = None,
):
    query_rewriter = QueryRewriter()
    reranker = Reranker()
    confidence_scorer = ConfidenceScorer()

    async def retrieval_node(state: ChatState) -> dict:
        query = state["user_message"]
        if settings.RAG_QUERY_REWRITE_ENABLED:
            query = query_rewriter.rewrite(query)

        node_results = retriever.retrieve(
            query,
            knowledge_source_id=state.get("knowledge_source_id"),
            document_id=state.get("document_id"),
        )
        retrieved = build_retrieved_chunks(node_results)

        if settings.GRAPH_RAG_ENABLED:
            retrieved = await _apply_graph_rag(query, state, retrieved, graph_retriever, fusion)

        if settings.RAG_RERANK_ENABLED:
            retrieved = reranker.rerank(query, retrieved)

        # Keep only the final number of chunks after reranking.
        retrieved = retrieved[: settings.HYBRID_FINAL_TOP_K]

        confidence = confidence_scorer.score(retrieved)
        compressed = compression.compress(retrieved)

        return {"retrieved_chunks": compressed, "confidence": confidence}

    return retrieval_node


async def _apply_graph_rag(
    query: str,
    state: ChatState,
    vector_results: list[RetrievedChunk],
    graph_retriever: "MultiHopRetriever | None",
    fusion: "GraphVectorFusion | None",
) -> list[RetrievedChunk]:
    """Runs MultiHopRetriever + GraphVectorFusion (both unmodified) and
    returns the fused RetrievedChunk list, or `vector_results`
    unchanged if scope is unavailable or anything fails.

    Always runs both HybridRetriever (already done by the caller) and
    MultiHopRetriever when this is reached -- no query classification,
    no "does this query need graph RAG" heuristic. Adaptive routing is
    explicitly out of scope for this stage.
    """
    document_id = _parse_uuid(state.get("document_id"))
    knowledge_source_id = _parse_uuid(state.get("knowledge_source_id"))

    if document_id is None and knowledge_source_id is None:
        # Never perform an unrestricted graph query -- vector
        # retrieval continues normally without graph augmentation.
        logger.info(
            "Graph RAG enabled but no document_id/knowledge_source_id "
            "scope in chat state; skipping graph retrieval for this "
            "request."
        )
        return vector_results

    try:
        if graph_retriever is not None and fusion is not None:
            # Test-injected instances.
            active_graph_retriever, active_fusion = graph_retriever, fusion
            graph_result = await active_graph_retriever.retrieve(
                query, knowledge_source_id=knowledge_source_id, document_id=document_id
            )
        else:
            from app.database.session import AsyncSessionLocal
            from app.knowledge_engine.retrieval.graph_retriever import GraphRetriever
            from app.knowledge_engine.retrieval.graph_vector_fusion import GraphVectorFusion
            from app.knowledge_engine.retrieval.multi_hop_retriever import MultiHopRetriever
            from app.repositories.graph_repository import (
                GraphEntityRepository,
                GraphEvidenceRepository,
                GraphRelationshipRepository,
            )

            active_fusion = GraphVectorFusion()
            async with AsyncSessionLocal() as session:
                active_graph_retriever = MultiHopRetriever(
                    GraphRetriever(
                        GraphEntityRepository(session),
                        GraphRelationshipRepository(session),
                        GraphEvidenceRepository(session),
                    )
                )
                graph_result = await active_graph_retriever.retrieve(
                    query, knowledge_source_id=knowledge_source_id, document_id=document_id
                )

        fused = active_fusion.fuse(
            vector_results,
            graph_result,
            document_id=document_id,
            knowledge_source_id=knowledge_source_id,
        )
    except Exception:
        # Graph RAG must never fail an otherwise-working vector
        # retrieval request -- log and fall back to vector-only.
        logger.exception(
            "Graph RAG retrieval/fusion failed; continuing with "
            "vector-only retrieval results."
        )
        return vector_results

    return [result.chunk for result in fused]
