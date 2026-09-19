"""Graph + Vector retrieval fusion (Sprint 2).

Combines ``HybridRetriever``'s output (already converted to
``RetrievedChunk`` via ``citation_builder.build_retrieved_chunks`` --
see that module) with ``GraphRetriever``'s output
(``GraphRetrievalResult``) into one deduplicated, ranked list.

Deliberately reuses ``RetrievedChunk``/``Citation``
(``app/knowledge_engine/models.py``) as the vector-side currency
instead of inventing a parallel representation -- that's the same
type ``retrieval_node.py``, the search API, the reranker, and
compression already consume, so a fused result is a drop-in
``RetrievedChunk`` wherever one of those already expects one.

The connection point between the two retrievers is chunk identity:
``RetrievedChunk.chunk_id`` and ``GraphEvidenceInfo.chunk_id`` both
trace back to the same ``HierarchicalChunk.node_id`` (see
``app/knowledge_engine/graph/graph.py``'s module docstring -- graph
evidence deliberately references that node id rather than a separate
chunk table). A relationship's evidence pointing at a chunk that
``HybridRetriever`` also surfaced is exactly the overlap case this
module is built to detect and merge, not duplicate.

No LLM calls, no embeddings, no DB access, no schema changes -- this
operates purely on already-fetched results. Not wired into
``retrieval_node.py``/``ChatOrchestrator`` yet; that's the next
sprint's job. ``HybridRetriever`` and ``GraphRetriever`` are both
unmodified and unaware this module exists.
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from app.knowledge_engine.models import Citation, RetrievedChunk
from app.knowledge_engine.retrieval.graph_retriever import (
    GraphRelationshipResult,
    GraphRetrievalResult,
)

DEFAULT_VECTOR_WEIGHT = 0.6
DEFAULT_GRAPH_WEIGHT = 0.4
DEFAULT_FUSION_LIMIT = 20


class GraphProvenance(BaseModel):
    """One graph relationship whose evidence points at a fused
    result's chunk -- everything requirement 3 asks to preserve
    (entity, relationship, evidence context, depth), scoped to what's
    relevant once a chunk has already been identified."""

    relationship_id: uuid.UUID
    relationship_type: str
    source_entity_name: str
    target_entity_name: str
    depth: int
    confidence: float | None = None
    chunk_id: str
    page_number: int | None = None
    source_text: str | None = None


class FusedResult(BaseModel):
    """One fused retrieval result. ``chunk`` is a normal
    ``RetrievedChunk`` -- from vector retrieval directly, or, for a
    graph-only match, synthesized from the relationship's evidence
    (see ``_synthesize_chunk_from_evidence``). ``graph_provenance`` is
    non-empty whenever this chunk is evidence for at least one graph
    relationship, regardless of whether it also came from vector
    retrieval -- that's exactly the ``origin == "both"`` case.
    """

    chunk: RetrievedChunk
    origin: str  # "vector" | "graph" | "both"
    graph_provenance: list[GraphProvenance] = Field(default_factory=list)
    fused_score: float = 0.0


def _normalized_vector_scores(chunks: list[RetrievedChunk]) -> dict[str, float]:
    """Vector scores scaled to [0, 1] by the batch's own max score --
    the same normalization Reranker already uses, so a fused score is
    comparable across chunks regardless of which retriever(s) produced
    the raw score."""
    if not chunks:
        return {}
    max_score = max((c.score for c in chunks), default=1.0) or 1.0
    return {c.chunk_id: c.score / max_score for c in chunks}


def _graph_relevance_score(depth: int) -> float:
    """Deterministic depth-decay: a relationship reached in fewer hops
    from a directly query-matched entity is considered more relevant.
    depth=1 (first hop) -> 0.5; depth=2 -> 0.333; etc. Explicitly a
    simple, explainable heuristic, not a trained/learned score."""
    return 1.0 / (1 + depth)


def _synthesize_chunk_from_evidence(
    *,
    chunk_id: str,
    source_text: str | None,
    page_number: int | None,
    document_id: uuid.UUID | None,
    knowledge_source_id: uuid.UUID | None,
) -> RetrievedChunk:
    """Builds a minimal RetrievedChunk for a chunk graph traversal
    found but vector retrieval didn't surface. Uses the relationship
    evidence's own source_text (the chunk's text as it was when
    extraction read it) since no vector-retrieval payload exists for
    this chunk in the current result set.

    Known limitation: GraphEvidence doesn't carry document_name or
    chunk_number, so this Citation is less complete than one
    build_citation() would produce from real Qdrant metadata --
    document_name falls back to "" (same fallback convention
    citation_builder.py already uses for missing metadata) unless the
    caller supplied document context. chunk_number defaults to 0.
    """
    return RetrievedChunk(
        text=source_text or "",
        score=0.0,
        chunk_id=chunk_id,
        citation=Citation(
            document_id=str(document_id) if document_id else "",
            document_name="",
            knowledge_source_id=str(knowledge_source_id) if knowledge_source_id else "",
            page_number=page_number,
            chunk_number=0,
            score=None,
        ),
    )


class GraphVectorFusion:
    """Deterministically combines HybridRetriever + GraphRetriever
    output. Stateless aside from its configured weights/limit --
    safe to construct once and reuse across requests.
    """

    def __init__(
        self,
        *,
        vector_weight: float = DEFAULT_VECTOR_WEIGHT,
        graph_weight: float = DEFAULT_GRAPH_WEIGHT,
        limit: int = DEFAULT_FUSION_LIMIT,
    ) -> None:
        if vector_weight < 0 or graph_weight < 0:
            raise ValueError("weights must be >= 0")
        if limit < 1:
            raise ValueError("limit must be >= 1")
        self._vector_weight = vector_weight
        self._graph_weight = graph_weight
        self._limit = limit

    def fuse(
        self,
        vector_results: list[RetrievedChunk],
        graph_result: GraphRetrievalResult | None,
        *,
        document_id: uuid.UUID | None = None,
        knowledge_source_id: uuid.UUID | None = None,
        limit: int | None = None,
    ) -> list[FusedResult]:
        """Combine one query's vector and graph results into a single
        ranked, deduplicated list.

        ``document_id``/``knowledge_source_id`` are used only to
        enrich synthesized graph-only citations (see
        ``_synthesize_chunk_from_evidence``) -- they do NOT perform or
        re-check scope filtering. Scope isolation is entirely
        GraphRetriever's responsibility (already enforced before its
        results ever reach this function); this function trusts
        whatever GraphRetrievalResult it's given and does not
        second-guess it. Pass the exact same scope you called
        GraphRetriever with, so citations are labeled correctly, not
        to "re-secure" anything.

        Deduplication key is ``chunk_id`` (see module docstring for
        why that's the correct join key). A chunk that's evidence for
        multiple relationships gets one FusedResult with multiple
        GraphProvenance entries, not multiple FusedResults.
        """
        effective_limit = limit if limit is not None else self._limit
        if effective_limit < 1:
            raise ValueError("limit must be >= 1")

        vector_score_by_chunk = _normalized_vector_scores(vector_results)
        chunk_by_id: dict[str, RetrievedChunk] = {c.chunk_id: c for c in vector_results}
        origin_by_chunk: dict[str, str] = {c.chunk_id: "vector" for c in vector_results}
        provenance_by_chunk: dict[str, list[GraphProvenance]] = {}

        relationships: list[GraphRelationshipResult] = (
            graph_result.relationships if graph_result is not None else []
        )
        for relationship in relationships:
            for ev in relationship.evidence:
                provenance = GraphProvenance(
                    relationship_id=relationship.relationship_id,
                    relationship_type=relationship.relationship_type,
                    source_entity_name=relationship.source.name,
                    target_entity_name=relationship.target.name,
                    depth=relationship.depth,
                    confidence=relationship.confidence,
                    chunk_id=ev.chunk_id,
                    page_number=ev.page_number,
                    source_text=ev.source_text,
                )
                provenance_by_chunk.setdefault(ev.chunk_id, []).append(provenance)

                if ev.chunk_id not in chunk_by_id:
                    chunk_by_id[ev.chunk_id] = _synthesize_chunk_from_evidence(
                        chunk_id=ev.chunk_id,
                        source_text=ev.source_text,
                        page_number=ev.page_number,
                        document_id=document_id,
                        knowledge_source_id=knowledge_source_id,
                    )
                    origin_by_chunk[ev.chunk_id] = "graph"
                elif origin_by_chunk[ev.chunk_id] == "vector":
                    origin_by_chunk[ev.chunk_id] = "both"

        fused: list[FusedResult] = []
        for chunk_id, chunk in chunk_by_id.items():
            graph_provenance = provenance_by_chunk.get(chunk_id, [])
            vector_component = vector_score_by_chunk.get(chunk_id, 0.0)
            graph_component = (
                max(_graph_relevance_score(p.depth) for p in graph_provenance)
                if graph_provenance
                else 0.0
            )
            fused_score = (
                self._vector_weight * vector_component + self._graph_weight * graph_component
            )
            fused.append(
                FusedResult(
                    chunk=chunk,
                    origin=origin_by_chunk[chunk_id],
                    graph_provenance=graph_provenance,
                    fused_score=fused_score,
                )
            )

        # Deterministic ordering: fused_score descending, chunk_id
        # ascending as a stable tie-break (never depends on dict/set
        # iteration order).
        fused.sort(key=lambda r: (-r.fused_score, r.chunk.chunk_id))
        return fused[:effective_limit]
