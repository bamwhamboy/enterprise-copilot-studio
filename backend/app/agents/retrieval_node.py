"""Retrieval node.

Runs (optionally) query rewriting, hybrid retrieval (Sprint 3B, reused
unchanged), and (optionally) re-ranking + confidence scoring, all
config-gated per Settings.RAG_QUERY_REWRITE_ENABLED /
Settings.RAG_RERANK_ENABLED.
"""

from __future__ import annotations

from app.agents.state import ChatState
from app.core.config import Settings
from app.knowledge_engine.citations.citation_builder import build_retrieved_chunks
from app.knowledge_engine.compression.compression_service import ContextCompressionService
from app.knowledge_engine.retrieval.confidence_scorer import ConfidenceScorer
from app.knowledge_engine.retrieval.hybrid_retriever import HybridRetriever
from app.knowledge_engine.retrieval.query_rewriter import QueryRewriter
from app.knowledge_engine.retrieval.reranker import Reranker


def make_retrieval_node(
    settings: Settings,
    retriever: HybridRetriever,
    compression: ContextCompressionService,
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

        if settings.RAG_RERANK_ENABLED:
           retrieved = reranker.rerank(query, retrieved)

    # Keep only the final number of chunks after reranking.
        retrieved = retrieved[: settings.HYBRID_FINAL_TOP_K]

        confidence = confidence_scorer.score(retrieved)
        compressed = compression.compress(retrieved)

        return {"retrieved_chunks": compressed, "confidence": confidence}

    return retrieval_node
