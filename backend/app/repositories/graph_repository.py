"""Repositories for GraphEntity / GraphRelationship / GraphEvidence.

Each ``find_by_*`` method here queries by the same natural key its
model's unique constraint covers (see ``app/models/graph.py``) -- these
are the lookups ``GraphExtractionService`` uses to make re-running
extraction for a document idempotent (check-then-create instead of
create-and-catch, with the DB constraint as the backstop for races).

The scope-filtered methods below (``search_by_scope``,
``get_many_by_ids``, ``list_outgoing_for_entities``,
``list_incoming_for_entities``, ``list_for_relationships``) exist for
``GraphRetriever`` (``app/knowledge_engine/retrieval/graph_retriever.py``)
-- retrieval-oriented lookups, not extraction-oriented ones. None of
the graph tables have their own ``knowledge_source_id`` column (only
``document_id``); knowledge-source scoping joins through
``Document.knowledge_source_id`` instead of adding one.
"""

import uuid

from sqlalchemy import select

from app.models.document import Document
from app.models.graph import GraphEntity, GraphEvidence, GraphRelationship
from app.repositories.base import BaseRepository


class GraphEntityRepository(BaseRepository[GraphEntity]):
    model = GraphEntity

    async def find_by_canonical_name(
        self, *, document_id: uuid.UUID, canonical_name: str, entity_type: str
    ) -> GraphEntity | None:
        stmt = select(GraphEntity).where(
            GraphEntity.document_id == document_id,
            GraphEntity.canonical_name == canonical_name,
            GraphEntity.entity_type == entity_type,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_document(self, document_id: uuid.UUID) -> list[GraphEntity]:
        stmt = select(GraphEntity).where(GraphEntity.document_id == document_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def search_by_scope(
        self,
        *,
        document_id: uuid.UUID | None = None,
        knowledge_source_id: uuid.UUID | None = None,
    ) -> list[GraphEntity]:
        """Candidate entities for retrieval, scoped to a document and/or
        a knowledge source. At least one of the two must be given --
        an unscoped, organization-wide entity scan is not something
        retrieval should ever do (see GraphRetriever's isolation
        guarantee).

        ``document_id`` narrows directly. ``knowledge_source_id`` joins
        through ``Document`` since graph tables don't carry that column
        themselves. Both may be given together (document_id then wins
        in practice, since it's already the more specific scope, but
        the join still applies as an extra, harmless constraint).
        """
        if document_id is None and knowledge_source_id is None:
            raise ValueError(
                "search_by_scope requires document_id and/or knowledge_source_id"
            )

        stmt = select(GraphEntity)
        if knowledge_source_id is not None:
            stmt = stmt.join(Document, Document.id == GraphEntity.document_id).where(
                Document.knowledge_source_id == knowledge_source_id
            )
        if document_id is not None:
            stmt = stmt.where(GraphEntity.document_id == document_id)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_many_by_ids(
        self,
        entity_ids: list[uuid.UUID],
        *,
        document_id: uuid.UUID | None = None,
        knowledge_source_id: uuid.UUID | None = None,
    ) -> list[GraphEntity]:
        """Batch entity lookup by id -- used to resolve relationship
        endpoints during traversal without relying on lazy-loaded ORM
        relationship attributes (which don't work implicitly under
        SQLAlchemy's async engine).

        ``document_id``/``knowledge_source_id`` are optional but should
        always be passed by scoped callers (GraphRetriever does): there
        is no FK/CHECK constraint tying a GraphRelationship's endpoints
        to its own document_id, so a relationship row scoped correctly
        by list_outgoing_for_entities/list_incoming_for_entities could
        still reference an entity from a different document (or a
        different knowledge source entirely) if that invariant were
        ever violated by a bug or manual data edit. Filtering here,
        not just trusting the relationship's own document_id, is what
        actually closes that gap -- without it, an out-of-scope entity
        would be silently returned and treated as a legitimate
        traversal result.
        """
        if not entity_ids:
            return []
        stmt = select(GraphEntity).where(GraphEntity.id.in_(entity_ids))
        if knowledge_source_id is not None:
            stmt = stmt.join(Document, Document.id == GraphEntity.document_id).where(
                Document.knowledge_source_id == knowledge_source_id
            )
        if document_id is not None:
            stmt = stmt.where(GraphEntity.document_id == document_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class GraphRelationshipRepository(BaseRepository[GraphRelationship]):
    model = GraphRelationship

    async def find_by_natural_key(
        self,
        *,
        document_id: uuid.UUID,
        source_entity_id: uuid.UUID,
        target_entity_id: uuid.UUID,
        relationship_type: str,
    ) -> GraphRelationship | None:
        stmt = select(GraphRelationship).where(
            GraphRelationship.document_id == document_id,
            GraphRelationship.source_entity_id == source_entity_id,
            GraphRelationship.target_entity_id == target_entity_id,
            GraphRelationship.relationship_type == relationship_type,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_document(self, document_id: uuid.UUID) -> list[GraphRelationship]:
        stmt = select(GraphRelationship).where(GraphRelationship.document_id == document_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    def _scope_clause(
        self,
        stmt,
        *,
        document_id: uuid.UUID | None,
        knowledge_source_id: uuid.UUID | None,
    ):
        """Applies the same document/knowledge-source scoping
        `search_by_scope` uses, as defense in depth: the entity ids
        passed to the two methods below are already scoped by the
        caller, but a relationship also carries its own document_id,
        so this re-asserts the scope at the edge level too rather than
        trusting entity-id membership alone."""
        if knowledge_source_id is not None:
            stmt = stmt.join(Document, Document.id == GraphRelationship.document_id).where(
                Document.knowledge_source_id == knowledge_source_id
            )
        if document_id is not None:
            stmt = stmt.where(GraphRelationship.document_id == document_id)
        return stmt

    async def list_outgoing_for_entities(
        self,
        entity_ids: list[uuid.UUID],
        *,
        document_id: uuid.UUID | None = None,
        knowledge_source_id: uuid.UUID | None = None,
    ) -> list[GraphRelationship]:
        """Relationships where one of ``entity_ids`` is the source."""
        if not entity_ids:
            return []
        stmt = select(GraphRelationship).where(
            GraphRelationship.source_entity_id.in_(entity_ids)
        )
        stmt = self._scope_clause(
            stmt, document_id=document_id, knowledge_source_id=knowledge_source_id
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_incoming_for_entities(
        self,
        entity_ids: list[uuid.UUID],
        *,
        document_id: uuid.UUID | None = None,
        knowledge_source_id: uuid.UUID | None = None,
    ) -> list[GraphRelationship]:
        """Relationships where one of ``entity_ids`` is the target."""
        if not entity_ids:
            return []
        stmt = select(GraphRelationship).where(
            GraphRelationship.target_entity_id.in_(entity_ids)
        )
        stmt = self._scope_clause(
            stmt, document_id=document_id, knowledge_source_id=knowledge_source_id
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class GraphEvidenceRepository(BaseRepository[GraphEvidence]):
    model = GraphEvidence

    async def find_by_relationship_and_chunk(
        self, *, relationship_id: uuid.UUID, chunk_id: str
    ) -> GraphEvidence | None:
        stmt = select(GraphEvidence).where(
            GraphEvidence.relationship_id == relationship_id,
            GraphEvidence.chunk_id == chunk_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_document(self, document_id: uuid.UUID) -> list[GraphEvidence]:
        stmt = select(GraphEvidence).where(GraphEvidence.document_id == document_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_for_relationships(
        self, relationship_ids: list[uuid.UUID]
    ) -> list[GraphEvidence]:
        """Batch evidence lookup for a set of relationships -- one
        query for a whole traversal's worth of edges, not one per
        edge."""
        if not relationship_ids:
            return []
        stmt = select(GraphEvidence).where(
            GraphEvidence.relationship_id.in_(relationship_ids)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
