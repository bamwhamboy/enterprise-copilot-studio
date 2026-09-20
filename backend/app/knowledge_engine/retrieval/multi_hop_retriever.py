"""True multi-hop Graph RAG retrieval, built on top of ``GraphRetriever``.

This is deliberately a thin composition layer, not a second traversal
engine: ``GraphRetriever.retrieve()`` already does the expensive part
(DB-backed, scope-safe BFS traversal up to a given depth, with its own
cycle/duplicate prevention -- see that module). ``MultiHopRetriever``
calls it exactly once per query, then does a second, cheap, in-memory
pass over the *already-fetched* (and already scope-filtered) edge list
to:

1. reconstruct explicit multi-hop reasoning *paths* from each seed
   entity outward (GraphRetriever returns a flat, deduplicated edge
   list -- it doesn't tell you "seed -> A -> B" as an ordered chain,
   which is what multi-hop *reasoning* actually needs to follow);
2. apply its own, finer-grained bounds (separate caps for seed
   entities, relationships, and evidence items -- GraphRetriever's own
   ``limit`` conflates seed count and relationship count into one
   number, by its own design);
3. sort everything by an explicit, documented, deterministic key
   (never relying on DB/dict/set iteration order); and
4. flatten evidence into one provenance-complete record per item (see
   ``MultiHopEvidence``).

No database queries happen here beyond the single delegated call to
``GraphRetriever.retrieve()``. No LLM calls, no embeddings. Scope
isolation is entirely inherited from that one call -- this module
performs no scope filtering of its own and trusts GraphRetriever's
guarantee completely, the same way ``graph_vector_fusion.py`` does.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from app.knowledge_engine.retrieval.graph_retriever import (
    GraphEntityMatch,
    GraphRelationshipResult,
    GraphRetriever,
)

DEFAULT_MAX_DEPTH = 2
DEFAULT_MAX_SEED_ENTITIES = 10
DEFAULT_MAX_RELATIONSHIPS = 50
DEFAULT_MAX_EVIDENCE_ITEMS = 100
# Headroom passed to GraphRetriever's own `limit` so ITS truncation
# never becomes the binding constraint before MultiHopRetriever's own
# (separately configurable) caps get a chance to apply -- see
# _resolve_graph_retriever_limit.
_GRAPH_RETRIEVER_LIMIT_HEADROOM = 200


@dataclass(frozen=True)
class MultiHopEvidence:
    """One evidence item, fully self-describing -- the chunk/page/text
    it came from, the relationship + entities it's evidence for, the
    hop count at which that relationship was reached, and confidence
    where available. Every field requirement 7 asks to preserve, in
    one flat record: each item alone is enough to support or cite a
    multi-hop claim, with no need to cross-reference back into a
    separate relationships list.
    """

    chunk_id: str
    source_text: str | None
    page_number: int | None
    relationship_id: uuid.UUID
    relationship_type: str
    source_entity: GraphEntityMatch
    target_entity: GraphEntityMatch
    depth: int
    confidence: float | None = None


@dataclass(frozen=True)
class MultiHopStep:
    """One edge within a reconstructed MultiHopPath."""

    relationship_id: uuid.UUID
    relationship_type: str
    source_entity: GraphEntityMatch
    target_entity: GraphEntityMatch
    depth: int
    confidence: float | None = None


@dataclass(frozen=True)
class MultiHopPath:
    """An explicit reasoning chain from one seed entity outward:
    seed -> step[0].target -> step[1].target -> ... Each step's
    source_entity is the previous step's target_entity (or the seed,
    for the first step) -- this is what distinguishes a "path" from
    GraphRetriever's flat, unordered edge list.

    ``depth`` is ``len(steps)`` (0 for a seed with no path beyond
    itself). A seed entity always has at least an empty-steps
    MultiHopPath in the result, mirroring GraphRetriever's own
    "matched entities are present even with zero relationships"
    guarantee.
    """

    seed_entity: GraphEntityMatch
    steps: tuple[MultiHopStep, ...] = ()

    @property
    def depth(self) -> int:
        return len(self.steps)

    @property
    def end_entity(self) -> GraphEntityMatch:
        return self.steps[-1].target_entity if self.steps else self.seed_entity


@dataclass(frozen=True)
class MultiHopResult:
    """Everything MultiHopRetriever found for one query, within scope.

    ``entities``/``relationships``/``evidence`` are flat, deduplicated
    lists -- the same shape GraphRetriever/graph_vector_fusion already
    expect, so this result is a drop-in source for either. ``paths``
    is the multi-hop-specific addition: explicit reasoning chains an
    answer-generation node can actually follow and narrate.
    """

    seed_entities: tuple[GraphEntityMatch, ...] = ()
    entities: tuple[GraphEntityMatch, ...] = ()
    relationships: tuple[GraphRelationshipResult, ...] = ()
    evidence: tuple[MultiHopEvidence, ...] = ()
    paths: tuple[MultiHopPath, ...] = ()
    depth_requested: int = 0
    depth_reached: int = 0

    @property
    def is_empty(self) -> bool:
        return not self.seed_entities


def _sort_key_entity(entity: GraphEntityMatch) -> tuple:
    # Documented deterministic ordering (requirement 9): shallower
    # (more central to the query) first, then alphabetical by
    # canonical_name for readability, then entity_id as a final,
    # always-unique tie-break. Never depends on DB/dict/set iteration
    # order.
    return (entity.depth, entity.canonical_name, str(entity.entity_id))


def _sort_key_relationship(relationship: GraphRelationshipResult) -> tuple:
    return (
        relationship.depth,
        relationship.relationship_type,
        str(relationship.source.entity_id),
        str(relationship.target.entity_id),
        str(relationship.relationship_id),
    )


def _sort_key_evidence(evidence: MultiHopEvidence) -> tuple:
    return (evidence.depth, evidence.chunk_id, str(evidence.relationship_id))


def _sort_key_path(path: MultiHopPath) -> tuple:
    return (
        path.depth,
        str(path.seed_entity.entity_id),
        tuple(str(step.relationship_id) for step in path.steps),
    )


class MultiHopRetriever:
    """Composes GraphRetriever into explicit, bounded, deterministic
    multi-hop reasoning paths -- no traversal/database logic of its
    own beyond one delegated call.
    """

    def __init__(
        self,
        graph_retriever: GraphRetriever,
        *,
        max_depth: int = DEFAULT_MAX_DEPTH,
        max_seed_entities: int = DEFAULT_MAX_SEED_ENTITIES,
        max_relationships: int = DEFAULT_MAX_RELATIONSHIPS,
        max_evidence_items: int = DEFAULT_MAX_EVIDENCE_ITEMS,
    ) -> None:
        if max_depth < 0:
            raise ValueError("max_depth must be >= 0")
        if max_seed_entities < 1 or max_relationships < 1 or max_evidence_items < 1:
            raise ValueError("max_seed_entities/max_relationships/max_evidence_items must be >= 1")
        self._graph_retriever = graph_retriever
        self._max_depth = max_depth
        self._max_seed_entities = max_seed_entities
        self._max_relationships = max_relationships
        self._max_evidence_items = max_evidence_items

    async def retrieve(
        self,
        query: str,
        *,
        knowledge_source_id: uuid.UUID | None = None,
        document_id: uuid.UUID | None = None,
        depth: int | None = None,
    ) -> MultiHopResult:
        """Match seed entities in ``query`` and return bounded,
        deterministic multi-hop reasoning paths within scope.

        ``depth`` defaults to this instance's configured ``max_depth``
        (2 by default) and is always clamped to it as a hard ceiling --
        a caller requesting a deeper traversal than configured gets the
        configured maximum, not an error and not the deeper request
        honored. ``depth=0`` returns seed entities only, no traversal
        (same semantics as GraphRetriever's own depth=0).

        Scope isolation is entirely GraphRetriever's guarantee,
        inherited unmodified from its one delegated call below -- see
        the module docstring.
        """
        requested_depth = self._max_depth if depth is None else depth
        if requested_depth < 0:
            raise ValueError("depth must be >= 0")
        effective_depth = min(requested_depth, self._max_depth)

        graph_result = await self._graph_retriever.retrieve(
            query,
            knowledge_source_id=knowledge_source_id,
            document_id=document_id,
            depth=effective_depth,
            limit=self._resolve_graph_retriever_limit(),
        )

        if graph_result.is_empty:
            return MultiHopResult(depth_requested=requested_depth, depth_reached=0)

        seed_entities = tuple(
            sorted(graph_result.matched_entities, key=_sort_key_entity)[: self._max_seed_entities]
        )
        seed_ids = {e.entity_id for e in seed_entities}

        # Reachability filter (bug fix): GraphRetriever's own BFS
        # expands from the FULL matched-seed set, so graph_result may
        # contain entities/relationships only reachable from a seed
        # that got truncated away just above. Re-deriving reachability
        # from ONLY the retained seeds -- via a second, in-memory BFS
        # over the edges GraphRetriever already returned, no new query
        # -- is what actually bounds the final result by
        # max_seed_entities, not just the seed_entities list itself.
        reachable_entity_ids, reachable_relationship_ids = self._reachable_from_seeds(
            seed_ids, graph_result.relationships, effective_depth
        )

        relationships = tuple(
            sorted(
                (
                    r
                    for r in graph_result.relationships
                    if r.relationship_id in reachable_relationship_ids
                ),
                key=_sort_key_relationship,
            )[: self._max_relationships]
        )

        entities = tuple(
            sorted(
                (e for e in graph_result.entities if e.entity_id in reachable_entity_ids),
                key=_sort_key_entity,
            )
        )

        evidence = self._flatten_evidence(relationships)

        paths = self._build_paths(seed_entities, relationships)

        depth_reached = max((r.depth for r in relationships), default=0)

        return MultiHopResult(
            seed_entities=seed_entities,
            entities=entities,
            relationships=relationships,
            evidence=evidence,
            paths=paths,
            depth_requested=requested_depth,
            depth_reached=depth_reached,
        )

    def _resolve_graph_retriever_limit(self) -> int:
        """GraphRetriever's own `limit` bounds both seed count and
        relationship count together. Request enough headroom that ITS
        truncation isn't what determines the final result -- this
        instance's own, separately configurable caps are applied
        afterward, in Python, over the (already scope-safe) result.
        """
        return max(
            self._max_seed_entities,
            self._max_relationships,
            _GRAPH_RETRIEVER_LIMIT_HEADROOM,
        )

    def _reachable_from_seeds(
        self,
        seed_ids: set[uuid.UUID],
        relationships: tuple[GraphRelationshipResult, ...],
        max_depth: int,
    ) -> tuple[set[uuid.UUID], set[uuid.UUID]]:
        """A second, in-memory BFS -- over the edges GraphRetriever
        already returned, no new query -- starting ONLY from the
        retained ``seed_ids`` (after max_seed_entities truncation),
        bounded by ``max_depth`` hops.

        GraphRetriever's own traversal expands from the *full* matched
        -seed set, so its result can contain entities/relationships
        only reachable from a seed that gets truncated away by
        max_seed_entities. This recomputes which of those are actually
        reachable from the seeds that survived truncation, which is
        what makes max_seed_entities a real bound on the final result
        rather than just a filter on the seed_entities list itself.

        Returns (reachable_entity_ids, reachable_relationship_ids);
        reachable_entity_ids always includes seed_ids even if they have
        no edges at all.
        """
        outgoing: dict[uuid.UUID, list[GraphRelationshipResult]] = {}
        incoming: dict[uuid.UUID, list[GraphRelationshipResult]] = {}
        for relationship in relationships:
            outgoing.setdefault(relationship.source.entity_id, []).append(relationship)
            incoming.setdefault(relationship.target.entity_id, []).append(relationship)

        reachable_entity_ids: set[uuid.UUID] = set(seed_ids)
        reachable_relationship_ids: set[uuid.UUID] = set()
        frontier = set(seed_ids)
        hop = 0
        while frontier and hop < max_depth:
            hop += 1
            next_frontier: set[uuid.UUID] = set()
            for entity_id in frontier:
                for edge in outgoing.get(entity_id, []) + incoming.get(entity_id, []):
                    other_id = (
                        edge.target.entity_id
                        if edge.source.entity_id == entity_id
                        else edge.source.entity_id
                    )
                    reachable_relationship_ids.add(edge.relationship_id)
                    if other_id not in reachable_entity_ids:
                        reachable_entity_ids.add(other_id)
                        next_frontier.add(other_id)
            frontier = next_frontier

        return reachable_entity_ids, reachable_relationship_ids

    def _flatten_evidence(
        self, relationships: tuple[GraphRelationshipResult, ...]
    ) -> tuple[MultiHopEvidence, ...]:
        seen: set[tuple[uuid.UUID, str]] = set()
        flat: list[MultiHopEvidence] = []
        for relationship in relationships:
            for ev in relationship.evidence:
                key = (relationship.relationship_id, ev.chunk_id)
                if key in seen:
                    # Defensive de-duplication (requirement 8): the DB's
                    # own unique constraint on (relationship_id, chunk_id)
                    # already prevents this structurally, but never trust
                    # that alone at this layer.
                    continue
                seen.add(key)
                flat.append(
                    MultiHopEvidence(
                        chunk_id=ev.chunk_id,
                        source_text=ev.source_text,
                        page_number=ev.page_number,
                        relationship_id=relationship.relationship_id,
                        relationship_type=relationship.relationship_type,
                        source_entity=relationship.source,
                        target_entity=relationship.target,
                        depth=relationship.depth,
                        confidence=relationship.confidence,
                    )
                )
        flat.sort(key=_sort_key_evidence)
        return tuple(flat[: self._max_evidence_items])

    def _build_paths(
        self,
        seed_entities: tuple[GraphEntityMatch, ...],
        relationships: tuple[GraphRelationshipResult, ...],
    ) -> tuple[MultiHopPath, ...]:
        """Reconstructs explicit hop-by-hop chains from each seed
        entity, using only the already-fetched (deduplicated,
        scope-safe) relationship list -- no new queries. A bounded
        DFS per seed, with a visited-set per branch (not global) so a
        cycle can't produce an infinite or ever-growing path, and a
        seed with multiple valid next hops yields multiple paths.
        """
        # Both directions: a step can be traversed via a relationship
        # where the current entity is either the source or the target
        # (GraphRetriever itself follows incoming and outgoing edges
        # the same way -- see its own module docstring).
        outgoing: dict[uuid.UUID, list[GraphRelationshipResult]] = {}
        incoming: dict[uuid.UUID, list[GraphRelationshipResult]] = {}
        for relationship in relationships:
            outgoing.setdefault(relationship.source.entity_id, []).append(relationship)
            incoming.setdefault(relationship.target.entity_id, []).append(relationship)

        all_paths: list[MultiHopPath] = []
        seen_path_keys: set[tuple] = set()

        for seed in seed_entities:
            branches: list[tuple[GraphEntityMatch, list[MultiHopStep], set[uuid.UUID]]] = [
                (seed, [], {seed.entity_id})
            ]
            # Always include the zero-step path for this seed, matching
            # GraphRetriever's "matched entities are present even with
            # zero relationships" guarantee.
            all_paths.append(MultiHopPath(seed_entity=seed, steps=()))

            while branches:
                current_entity, steps_so_far, visited = branches.pop()
                if len(steps_so_far) >= self._max_depth:
                    continue

                next_edges = outgoing.get(current_entity.entity_id, []) + incoming.get(
                    current_entity.entity_id, []
                )
                for edge in next_edges:
                    next_entity = (
                        edge.target if edge.source.entity_id == current_entity.entity_id
                        else edge.source
                    )
                    if next_entity.entity_id in visited:
                        continue  # cycle protection: never revisit within one path

                    step = MultiHopStep(
                        relationship_id=edge.relationship_id,
                        relationship_type=edge.relationship_type,
                        source_entity=current_entity,
                        target_entity=next_entity,
                        depth=len(steps_so_far) + 1,
                        confidence=edge.confidence,
                    )
                    new_steps = [*steps_so_far, step]
                    path_key = (seed.entity_id, tuple(s.relationship_id for s in new_steps))
                    if path_key not in seen_path_keys:
                        seen_path_keys.add(path_key)
                        all_paths.append(MultiHopPath(seed_entity=seed, steps=tuple(new_steps)))

                    branches.append((next_entity, new_steps, visited | {next_entity.entity_id}))

        all_paths.sort(key=_sort_key_path)
        return tuple(all_paths)
