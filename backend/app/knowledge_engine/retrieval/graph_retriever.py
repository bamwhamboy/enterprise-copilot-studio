"""Graph retrieval foundation (Sprint 2).

Entity matching + bounded graph traversal over the already-extracted
knowledge graph (``GraphEntity``/``GraphRelationship``/``GraphEvidence``
-- see ``app/knowledge_engine/graph/``). This is deliberately the
*retrieval* half only: no fusion with ``HybridRetriever``, no changes
to ``retrieval_node.py``/``ChatOrchestrator``/LangGraph orchestration.
Wiring this into the chat path is the next sprint's Graph+Vector
Fusion work.

Entity matching here is intentionally simple: the query text is
normalized with the same ``normalize_canonical_name()`` extraction
already uses (see ``app/knowledge_engine/graph/graph_extraction_service.py``),
and an entity is considered "matched" if its ``canonical_name`` appears
as a substring of the normalized query. No LLM call, no embeddings, no
second vector index -- deterministic string containment only. This is
a foundation, not a ranking model; a real similarity/embedding-based
matcher is future work, not this sprint's.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from app.knowledge_engine.graph.graph_extraction_service import normalize_canonical_name
from app.models.graph import GraphEntity, GraphRelationship
from app.repositories.graph_repository import (
    GraphEntityRepository,
    GraphEvidenceRepository,
    GraphRelationshipRepository,
)

DEFAULT_TRAVERSAL_DEPTH = 1
DEFAULT_RESULT_LIMIT = 20


@dataclass(frozen=True)
class GraphEvidenceInfo:
    """Provenance for one relationship: where it was extracted from."""

    chunk_id: str
    page_number: int | None
    source_text: str | None


@dataclass(frozen=True)
class GraphEntityMatch:
    """One entity node encountered during retrieval -- either a direct
    query match (``depth=0``) or reached via traversal (``depth>=1``,
    the hop count at which it was first discovered)."""

    entity_id: uuid.UUID
    name: str
    canonical_name: str
    entity_type: str
    depth: int
    # Reserved for a future scoring model (e.g. depth-decay or a real
    # similarity score once entity matching stops being pure string
    # containment). Deterministic substring matching has no natural
    # continuous score, so this is always None in this foundation.
    score: float | None = None


@dataclass(frozen=True)
class GraphRelationshipResult:
    """One traversed edge, with full provenance -- the unit later
    fusion with HybridRetriever's chunk-level results is expected to
    consume."""

    relationship_id: uuid.UUID
    relationship_type: str
    source: GraphEntityMatch
    target: GraphEntityMatch
    confidence: float | None
    depth: int  # hop count at which this edge was traversed (1 = first hop)
    evidence: list[GraphEvidenceInfo] = field(default_factory=list)
    # Reserved for future fusion weighting; see GraphEntityMatch.score.
    score: float | None = None


@dataclass(frozen=True)
class GraphRetrievalResult:
    """Everything GraphRetriever found for one query, within scope.

    ``matched_entities`` are exactly the depth-0 entities the query
    text matched (before any traversal) -- present even if they have
    no relationships at all, so the caller knows the query touched a
    known entity either way. ``relationships`` are the traversed edges
    (deduplicated; empty if depth=0 or no edges exist).
    ``entities`` is every entity encountered, seeds and traversed
    alike, deduplicated by id.
    """

    matched_entities: list[GraphEntityMatch] = field(default_factory=list)
    relationships: list[GraphRelationshipResult] = field(default_factory=list)
    entities: list[GraphEntityMatch] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not self.matched_entities


def _to_match(entity: GraphEntity, *, depth: int) -> GraphEntityMatch:
    return GraphEntityMatch(
        entity_id=entity.id,
        name=entity.name,
        canonical_name=entity.canonical_name,
        entity_type=entity.entity_type,
        depth=depth,
    )


class GraphRetriever:
    """Matches entities mentioned in a query and traverses their
    relationships up to a bounded depth, within a document and/or
    knowledge-source scope.
    """

    def __init__(
        self,
        entities: GraphEntityRepository,
        relationships: GraphRelationshipRepository,
        evidence: GraphEvidenceRepository,
    ) -> None:
        self._entities = entities
        self._relationships = relationships
        self._evidence = evidence

    async def retrieve(
        self,
        query: str,
        *,
        knowledge_source_id: uuid.UUID | None = None,
        document_id: uuid.UUID | None = None,
        depth: int = DEFAULT_TRAVERSAL_DEPTH,
        limit: int = DEFAULT_RESULT_LIMIT,
    ) -> GraphRetrievalResult:
        """Match entities in ``query`` and traverse their relationships.

        Exactly one scope requirement: at least one of
        ``knowledge_source_id``/``document_id`` must be given (enforced
        by ``GraphEntityRepository.search_by_scope``) -- there is no
        "search everything" mode, to guarantee isolation between
        knowledge sources/documents is never accidentally bypassed.

        ``depth`` bounds the number of hops traversed outward from the
        matched entities (0 = matching only, no traversal). ``limit``
        bounds both how many matched entities seed the traversal and
        how many relationships are returned in total -- a defensive
        cap, not a relevance-ranked top-k (this foundation has no
        continuous relevance score to rank by; see GraphEntityMatch.score).

        Cycle/duplicate prevention: an entity is only ever traversed
        *from* once (a global visited-entity set, updated hop by hop,
        so A->B->A can't loop), and a relationship is only ever
        returned once even if reachable via multiple paths (a visited
        -relationship set) or via both its outgoing-of-source and
        incoming-of-target queries in the same hop.
        """
        if depth < 0:
            raise ValueError("depth must be >= 0")
        if limit < 1:
            raise ValueError("limit must be >= 1")

        normalized_query = normalize_canonical_name(query) if query and query.strip() else ""
        if not normalized_query:
            return GraphRetrievalResult()

        candidates = await self._entities.search_by_scope(
            document_id=document_id, knowledge_source_id=knowledge_source_id
        )
        seed_entities = [
            entity
            for entity in candidates
            if entity.canonical_name and entity.canonical_name in normalized_query
        ][:limit]

        if not seed_entities:
            return GraphRetrievalResult()

        entities_by_id: dict[uuid.UUID, GraphEntity] = {e.id: e for e in seed_entities}
        entity_depth: dict[uuid.UUID, int] = {e.id: 0 for e in seed_entities}
        visited_entity_ids: set[uuid.UUID] = set(entity_depth)
        visited_relationship_ids: set[uuid.UUID] = set()
        relationship_results: list[GraphRelationshipResult] = []

        frontier_ids = list(visited_entity_ids)
        hop = 0
        while frontier_ids and hop < depth and len(relationship_results) < limit:
            hop += 1

            outgoing = await self._relationships.list_outgoing_for_entities(
                frontier_ids, document_id=document_id, knowledge_source_id=knowledge_source_id
            )
            incoming = await self._relationships.list_incoming_for_entities(
                frontier_ids, document_id=document_id, knowledge_source_id=knowledge_source_id
            )

            new_edges: list[GraphRelationship] = []
            for edge in outgoing + incoming:
                if edge.id in visited_relationship_ids:
                    continue
                visited_relationship_ids.add(edge.id)
                new_edges.append(edge)

            missing_ids = {
                eid
                for edge in new_edges
                for eid in (edge.source_entity_id, edge.target_entity_id)
                if eid not in entities_by_id
            }
            if missing_ids:
                for fetched in await self._entities.get_many_by_ids(
                    list(missing_ids),
                    document_id=document_id,
                    knowledge_source_id=knowledge_source_id,
                ):
                    entities_by_id[fetched.id] = fetched

            next_frontier_ids: set[uuid.UUID] = set()
            for edge in new_edges:
                if len(relationship_results) >= limit:
                    break
                source = entities_by_id.get(edge.source_entity_id)
                target = entities_by_id.get(edge.target_entity_id)
                if source is None or target is None:
                    # This is the actual isolation enforcement point,
                    # not just a defensive fallback: get_many_by_ids is
                    # scoped identically to search_by_scope, so a
                    # relationship endpoint outside the requested scope
                    # never enters entities_by_id in the first place --
                    # the edge is silently dropped here instead of
                    # traversing through it. (A relationship's own
                    # document_id being in-scope does not guarantee its
                    # endpoints are, since nothing in the schema ties
                    # the two together -- see get_many_by_ids's
                    # docstring.)
                    continue

                for entity, entity_id in ((source, edge.source_entity_id), (target, edge.target_entity_id)):
                    if entity_id not in entity_depth:
                        entity_depth[entity_id] = hop
                    if entity_id not in visited_entity_ids:
                        next_frontier_ids.add(entity_id)

                relationship_results.append(
                    GraphRelationshipResult(
                        relationship_id=edge.id,
                        relationship_type=edge.relationship_type,
                        source=_to_match(source, depth=entity_depth[source.id]),
                        target=_to_match(target, depth=entity_depth[target.id]),
                        confidence=edge.confidence,
                        depth=hop,
                    )
                )

            visited_entity_ids |= next_frontier_ids
            frontier_ids = list(next_frontier_ids)

        if relationship_results:
            evidence_rows = await self._evidence.list_for_relationships(
                [r.relationship_id for r in relationship_results]
            )
            evidence_by_relationship: dict[uuid.UUID, list[GraphEvidenceInfo]] = {}
            for row in evidence_rows:
                evidence_by_relationship.setdefault(row.relationship_id, []).append(
                    GraphEvidenceInfo(
                        chunk_id=row.chunk_id,
                        page_number=row.page_number,
                        source_text=row.source_text,
                    )
                )
            relationship_results = [
                GraphRelationshipResult(
                    relationship_id=r.relationship_id,
                    relationship_type=r.relationship_type,
                    source=r.source,
                    target=r.target,
                    confidence=r.confidence,
                    depth=r.depth,
                    evidence=evidence_by_relationship.get(r.relationship_id, []),
                )
                for r in relationship_results
            ]

        matched_entities = [_to_match(e, depth=0) for e in seed_entities]
        all_entities = [
            _to_match(entities_by_id[eid], depth=entity_depth[eid]) for eid in entity_depth
        ]

        return GraphRetrievalResult(
            matched_entities=matched_entities,
            relationships=relationship_results,
            entities=all_entities,
        )
