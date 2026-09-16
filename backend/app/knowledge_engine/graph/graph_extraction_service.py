"""Graph RAG extraction orchestration.

Takes the same ``HierarchicalChunk`` objects ``IndexingService`` already
produces (see ``app/knowledge_engine/chunking/hierarchical_chunker.py``)
and, for each one, extracts entities/relationships via
``GraphExtractor`` and persists them as ``GraphEntity`` /
``GraphRelationship`` / ``GraphEvidence`` rows.

Deliberately NOT wired into ``IndexingService`` yet -- this is the
extraction/persistence layer only. Nothing here touches Qdrant, the
embedding model, BM25, chunking itself, chat orchestration, or answer
generation; it only *consumes* the chunks that pipeline already
produced.

Idempotency: entities are resolved (not re-created) by
``(document_id, canonical_name, entity_type)``; relationships by
``(document_id, source_entity_id, target_entity_id,
relationship_type)``; evidence by ``(relationship_id, chunk_id)``.
These are exactly the natural keys the DB unique constraints in
``app/models/graph.py`` enforce, so re-running extraction for the same
document (e.g. after a re-index) reuses existing rows instead of
duplicating them -- the DB constraint is the backstop if two
extraction runs ever race.

Canonical-name normalization: the LLM's ``canonical_name`` for the same
real-world entity can vary in trivial, non-semantic ways across chunks
-- "registration_fees" in one chunk, "registration fees" in another.
Since entity resolution keys on ``canonical_name`` exactly, this alone
was enough to create duplicate entities for the same thing.
``normalize_canonical_name`` below is applied consistently everywhere
a canonical name is used for lookup, caching, or persistence (entity
resolution AND relationship source/target resolution), so those two
strings resolve to one entity. This is deliberately *syntactic* only
(whitespace/case/separator normalization) -- it never merges names
that are merely semantically similar; "federal awards" and "federally
sponsored awards" remain distinct entities since their normalized
forms differ.

Failure isolation: each chunk's extraction + persistence is wrapped in
its own try/except and its own commit. A chunk that fails (malformed
LLM output, an unexpected DB error) is recorded in the returned
result's ``errors`` and does not prevent any other chunk in the
document from being processed.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.knowledge_engine.graph.extractor import GraphExtractionError, GraphExtractor
from app.knowledge_engine.models import HierarchicalChunk
from app.models.graph import GraphEntity, GraphEvidence, GraphRelationship
from app.repositories.graph_repository import (
    GraphEntityRepository,
    GraphEvidenceRepository,
    GraphRelationshipRepository,
)

logger = get_logger(__name__)

_WHITESPACE_RE = re.compile(r"\s+")


def normalize_canonical_name(name: str) -> str:
    """Deterministic, syntactic-only normalization for a canonical
    entity name -- the single function used everywhere a canonical
    name is looked up, cached, or persisted, so entity/relationship
    resolution is consistent across chunks.

    Strips surrounding whitespace, lowercases, replaces underscores
    and hyphens with spaces, and collapses repeated whitespace. Does
    NOT perform semantic normalization, stemming, or synonym merging:
    two names with different words (or different meaning) always stay
    distinct here even if a human would consider them related --
    that kind of merging is out of scope for this function on purpose.

    >>> normalize_canonical_name("registration_fees")
    'registration fees'
    >>> normalize_canonical_name("Registration   Fees")
    'registration fees'
    >>> normalize_canonical_name("federally sponsored awards") == \
normalize_canonical_name("federal awards")
    False
    """
    normalized = name.strip().lower()
    normalized = normalized.replace("_", " ").replace("-", " ")
    normalized = _WHITESPACE_RE.sub(" ", normalized)
    return normalized.strip()


@dataclass
class ChunkExtractionError:
    chunk_id: str
    error: str


@dataclass
class GraphExtractionResult:
    """Summary of one ``extract_for_document`` run."""

    document_id: uuid.UUID
    chunks_processed: int = 0
    chunks_succeeded: int = 0
    chunks_failed: int = 0
    entities_created: int = 0
    relationships_created: int = 0
    evidence_created: int = 0
    errors: list[ChunkExtractionError] = field(default_factory=list)


@dataclass
class _ChunkCounts:
    """Per-chunk creation counters.

    Kept separate from ``GraphExtractionResult`` so a failed chunk's
    counts can simply be discarded rather than merged -- see
    ``extract_for_document``.
    """

    entities_created: int = 0
    relationships_created: int = 0
    evidence_created: int = 0


class GraphExtractionService:
    """Extracts and persists the knowledge graph for a document's chunks."""

    def __init__(self, session: AsyncSession, extractor: GraphExtractor) -> None:
        self.session = session
        self.extractor = extractor
        self.entities = GraphEntityRepository(session)
        self.relationships = GraphRelationshipRepository(session)
        self.evidence = GraphEvidenceRepository(session)

    async def extract_for_document(
        self, document_id: uuid.UUID, chunks: list[HierarchicalChunk]
    ) -> GraphExtractionResult:
        result = GraphExtractionResult(document_id=document_id)

        # Document-level cache so entities that recur across multiple
        # chunks (e.g. "Acme Corp" mentioned in several paragraphs)
        # resolve to the same row instead of being re-queried/re-created
        # every time -- keyed exactly on the natural key the DB
        # constraint covers, with the canonical name normalized so
        # e.g. "registration_fees" and "registration fees" share one
        # cache entry.
        entity_cache: dict[tuple[str, str], GraphEntity] = {}
        for existing in await self.entities.list_for_document(document_id):
            key = (normalize_canonical_name(existing.canonical_name), existing.entity_type)
            entity_cache[key] = existing

        for chunk in chunks:
            result.chunks_processed += 1
            # Work against a local copy of the cache and local counters
            # for this chunk only. If anything in this chunk fails, we
            # discard both entirely rather than merge them into shared
            # state -- the DB rollback below undoes the persisted rows,
            # but it can't undo Python objects already sitting in
            # `entity_cache`/`result`, so those must never be mutated
            # directly until the chunk's commit has actually succeeded.
            local_cache = dict(entity_cache)
            local_counts = _ChunkCounts()
            try:
                await self._process_chunk(document_id, chunk, local_cache, local_counts)
                await self.session.commit()
                result.chunks_succeeded += 1
                # Only now, after a successful commit, do the entities
                # created/reused by this chunk become visible to later
                # chunks, and only now do this chunk's counts count.
                entity_cache.update(local_cache)
                result.entities_created += local_counts.entities_created
                result.relationships_created += local_counts.relationships_created
                result.evidence_created += local_counts.evidence_created
            except Exception as exc:  # noqa: BLE001 - deliberately broad; see docstring
                # Isolation: one bad chunk (malformed LLM JSON, an
                # unexpected DB error, anything) must not stop the rest
                # of the document from being processed, and must not
                # leave stale ORM objects or inflated counts behind --
                # local_cache/local_counts are simply discarded here,
                # never merged into entity_cache/result.
                logger.exception(
                    "Graph extraction failed for chunk %s of document %s",
                    chunk.node_id,
                    document_id,
                )
                await self.session.rollback()
                result.chunks_failed += 1
                result.errors.append(
                    ChunkExtractionError(chunk_id=chunk.node_id, error=str(exc))
                )

        return result

    async def _process_chunk(
        self,
        document_id: uuid.UUID,
        chunk: HierarchicalChunk,
        entity_cache: dict[tuple[str, str], GraphEntity],
        counts: "_ChunkCounts",
    ) -> None:
        try:
            extraction = await self.extractor.extract(chunk.text)
        except GraphExtractionError:
            # Re-raised as-is -- caught by extract_for_document's
            # per-chunk try/except, same as any other chunk failure.
            raise

        chunk_entities: dict[str, GraphEntity] = {}
        for extracted in extraction.entities:
            # Normalized once here, and used identically for the cache
            # key, the DB lookup, and (further below) what actually
            # gets persisted -- so all three agree on what counts as
            # "the same" canonical name.
            canonical_name = normalize_canonical_name(extracted.canonical_name)
            key = (canonical_name, extracted.entity_type)
            entity = entity_cache.get(key)
            if entity is None:
                entity = await self.entities.find_by_canonical_name(
                    document_id=document_id,
                    canonical_name=canonical_name,
                    entity_type=extracted.entity_type,
                )
            if entity is None:
                entity = GraphEntity(
                    document_id=document_id,
                    name=extracted.name,
                    canonical_name=canonical_name,
                    entity_type=extracted.entity_type,
                )
                await self.entities.create(entity)
                counts.entities_created += 1
            entity_cache[key] = entity
            chunk_entities[canonical_name] = entity

        for extracted_rel in extraction.relationships:
            # Same normalization applied to the relationship's
            # source/target references before looking them up in
            # chunk_entities -- otherwise "registration_fees" as a
            # relationship's source_entity would fail to match an
            # entity cached under the normalized key "registration fees".
            source = chunk_entities.get(normalize_canonical_name(extracted_rel.source_entity))
            target = chunk_entities.get(normalize_canonical_name(extracted_rel.target_entity))
            if source is None or target is None:
                # Belt-and-suspenders: GraphExtractor already validates
                # this, but a chunk's persistence should never trust an
                # invariant enforced only in another module.
                logger.warning(
                    "Skipping relationship with unresolved entity reference "
                    "(source=%r target=%r) for chunk %s",
                    extracted_rel.source_entity,
                    extracted_rel.target_entity,
                    chunk.node_id,
                )
                continue

            relationship = await self.relationships.find_by_natural_key(
                document_id=document_id,
                source_entity_id=source.id,
                target_entity_id=target.id,
                relationship_type=extracted_rel.relationship_type,
            )
            if relationship is None:
                relationship = GraphRelationship(
                    document_id=document_id,
                    source_entity_id=source.id,
                    target_entity_id=target.id,
                    relationship_type=extracted_rel.relationship_type,
                    confidence=extracted_rel.confidence,
                )
                await self.relationships.create(relationship)
                counts.relationships_created += 1

            existing_evidence = await self.evidence.find_by_relationship_and_chunk(
                relationship_id=relationship.id, chunk_id=chunk.node_id
            )
            if existing_evidence is None:
                await self.evidence.create(
                    GraphEvidence(
                        relationship_id=relationship.id,
                        document_id=document_id,
                        chunk_id=chunk.node_id,
                        page_number=chunk.metadata.page_number,
                        source_text=chunk.text,
                    )
                )
                counts.evidence_created += 1
