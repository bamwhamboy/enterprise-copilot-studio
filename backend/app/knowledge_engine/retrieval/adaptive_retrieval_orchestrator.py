"""AdaptiveRetrievalOrchestrator (Sprint: Adaptive Retrieval Orchestration).

Decides HYBRID / GRAPH / HYBRID_GRAPH and delegates to the existing,
unmodified retrieval components. Contains zero retrieval, traversal,
fusion, scoring, or dedup logic of its own -- every result comes from
HybridRetriever.retrieve(), MultiHopRetriever.retrieve(), or
GraphVectorFusion.fuse(), called as-is. Graph-to-chunk conversion is
always delegated to GraphVectorFusion.fuse() (even in GRAPH-only mode,
via vector_results=[]) rather than writing a second conversion path --
see graph_vector_fusion.py's own module docstring.

No LLM call for routing. The mode-selection rule is a small, injected,
deterministic ModeSelector (see keyword_mode_selector below) --
swapping in a JEV-based classifier later means providing a different
ModeSelector, not touching this class.

Two safety invariants are enforced by this class directly, never
delegated to the ModeSelector (a future/misbehaving selector cannot
override them):
- Settings.GRAPH_RAG_ENABLED is the absolute master switch -- False
  forces HYBRID regardless of anything else.
- No document_id/knowledge_source_id -- forces HYBRID; graph retrieval
  never runs unscoped.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from app.core.config import Settings
from app.core.logging import get_logger
from app.knowledge_engine.citations.citation_builder import build_retrieved_chunks
from app.knowledge_engine.models import RetrievedChunk
from app.knowledge_engine.retrieval.hybrid_retriever import HybridRetriever

# Deferred to TYPE_CHECKING only -- same reasoning as retrieval_node.py:
# importing these for real pulls in LLMGateway/litellm transitively.
if TYPE_CHECKING:
    from app.knowledge_engine.retrieval.graph_vector_fusion import GraphVectorFusion
    from app.knowledge_engine.retrieval.multi_hop_retriever import MultiHopRetriever

logger = get_logger(__name__)


class RetrievalMode(str, Enum):
    HYBRID = "hybrid"
    GRAPH = "graph"
    HYBRID_GRAPH = "hybrid_graph"


@dataclass(frozen=True)
class RoutingContext:
    """What a ModeSelector gets to decide from -- deliberately just
    the query and scope, no query results, no DB access. A JEV-based
    selector replacing keyword_mode_selector later still only needs
    this."""

    query: str
    document_id: uuid.UUID | None
    knowledge_source_id: uuid.UUID | None


ModeSelector = Callable[[RoutingContext], RetrievalMode]


# Deliberately simple, explainable, non-exhaustive pattern sets -- this
# is the "small deterministic ModeSelector for this increment" the
# task asks for, not a claim of real NLU. Checked in order: multi-hop
# patterns first (more specific signal), then relationship patterns,
# else HYBRID.
_MULTI_HOP_PATTERNS = (
    "and then",
    "which in turn",
    "eventually",
    "downstream",
    "indirectly",
    "chain of",
    "path from",
    "multi-step",
    "multiple steps",
    "ultimately",
    "as a result of",
    "through which",
    "leads to",
)

_RELATIONSHIP_PATTERNS = (
    "relationship between",
    "relationship with",
    "related to",
    "relation to",
    "connected to",
    "connection between",
    "associated with",
    "linked to",
    "affiliated with",
    "who is",
    "what is the link",
)


def keyword_mode_selector(context: RoutingContext) -> RetrievalMode:
    """Default ModeSelector for this increment. No LLM, no embeddings --
    plain substring matching against the (lowercased) query text."""
    text = context.query.lower()
    if any(pattern in text for pattern in _MULTI_HOP_PATTERNS):
        return RetrievalMode.HYBRID_GRAPH
    if any(pattern in text for pattern in _RELATIONSHIP_PATTERNS):
        return RetrievalMode.GRAPH
    return RetrievalMode.HYBRID


class AdaptiveRetrievalOrchestrator:
    """Routes one query to HYBRID / GRAPH / HYBRID_GRAPH and returns
    list[RetrievedChunk] -- the same contract HybridRetriever's own
    output (after build_retrieved_chunks) and GraphVectorFusion's
    output (after unwrapping .chunk) already produce, so callers
    (retrieval_node.py) don't need to know which mode ran.
    """

    def __init__(
        self,
        settings: Settings,
        hybrid_retriever: HybridRetriever,
        graph_retriever: "MultiHopRetriever | None" = None,
        fusion: "GraphVectorFusion | None" = None,
        mode_selector: ModeSelector = keyword_mode_selector,
    ) -> None:
        self._settings = settings
        self._hybrid_retriever = hybrid_retriever
        self._graph_retriever = graph_retriever
        self._fusion = fusion
        self._mode_selector = mode_selector

    async def retrieve(
        self,
        query: str,
        *,
        document_id: uuid.UUID | None = None,
        knowledge_source_id: uuid.UUID | None = None,
    ) -> list[RetrievedChunk]:
        mode = self._resolve_mode(query, document_id, knowledge_source_id)

        if mode is RetrievalMode.HYBRID:
            return self._run_hybrid(query, document_id, knowledge_source_id)
        if mode is RetrievalMode.GRAPH:
            return await self._run_graph_only(query, document_id, knowledge_source_id)
        return await self._run_hybrid_graph(query, document_id, knowledge_source_id)

    def _resolve_mode(
        self,
        query: str,
        document_id: uuid.UUID | None,
        knowledge_source_id: uuid.UUID | None,
    ) -> RetrievalMode:
        if not self._settings.GRAPH_RAG_ENABLED:
            return RetrievalMode.HYBRID
        if document_id is None and knowledge_source_id is None:
            return RetrievalMode.HYBRID
        if self._graph_retriever is None or self._fusion is None:
            # Misconfiguration guard: adaptive+graph-RAG enabled but
            # this instance wasn't given graph components -- never
            # attempt to call None.
            return RetrievalMode.HYBRID
        return self._mode_selector(
            RoutingContext(
                query=query, document_id=document_id, knowledge_source_id=knowledge_source_id
            )
        )

    def _run_hybrid(
        self, query: str, document_id: uuid.UUID | None, knowledge_source_id: uuid.UUID | None
    ) -> list[RetrievedChunk]:
        node_results = self._hybrid_retriever.retrieve(
            query, knowledge_source_id=knowledge_source_id, document_id=document_id
        )
        return build_retrieved_chunks(node_results)

    async def _run_graph_only(
        self, query: str, document_id: uuid.UUID | None, knowledge_source_id: uuid.UUID | None
    ) -> list[RetrievedChunk]:
        try:
            graph_result = await self._graph_retriever.retrieve(
                query, knowledge_source_id=knowledge_source_id, document_id=document_id
            )
            fused = self._fusion.fuse(
                [], graph_result, document_id=document_id, knowledge_source_id=knowledge_source_id
            )
            return [result.chunk for result in fused]
        except Exception:
            # GRAPH mode never called HybridRetriever above, so on
            # failure there are no vector results to fall back to --
            # get some now, reactively, rather than return nothing.
            logger.exception(
                "Graph-only retrieval failed; falling back to HybridRetriever."
            )
            return self._run_hybrid(query, document_id, knowledge_source_id)

    async def _run_hybrid_graph(
        self, query: str, document_id: uuid.UUID | None, knowledge_source_id: uuid.UUID | None
    ) -> list[RetrievedChunk]:
        vector_results = self._run_hybrid(query, document_id, knowledge_source_id)
        try:
            graph_result = await self._graph_retriever.retrieve(
                query, knowledge_source_id=knowledge_source_id, document_id=document_id
            )
            fused = self._fusion.fuse(
                vector_results,
                graph_result,
                document_id=document_id,
                knowledge_source_id=knowledge_source_id,
            )
            return [result.chunk for result in fused]
        except Exception:
            logger.exception(
                "Graph retrieval/fusion failed; falling back to the "
                "vector results already retrieved."
            )
            return vector_results
