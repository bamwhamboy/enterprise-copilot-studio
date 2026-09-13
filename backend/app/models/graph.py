"""Graph RAG persistence models.

These three tables hold the knowledge graph extracted from a document,
stored alongside the existing relational schema in
PostgreSQL/Supabase. This is deliberately independent of the existing
Qdrant vector pipeline (Document -> HierarchicalChunk[] -> TextNode[]
-> embeddings -> Qdrant) -- nothing here touches that flow.

There is currently no PostgreSQL chunk table (chunks only exist as
HierarchicalChunk/TextNode objects that get embedded into Qdrant), so
``GraphEvidence.chunk_id`` is a plain string referencing that existing
node_id rather than a foreign key. This is the same pattern already
used by other tables that reference identifiers outside their own
FK graph (e.g. ``ConversationSession.copilot_id`` in conversation.py).

Provenance chain: GraphRelationship -> GraphEvidence -> (document_id,
chunk_id, page_number, source_text), so any extracted relationship can
be traced back to the exact chunk/page/passage it was derived from.

Re-indexing idempotency: a document can be re-indexed (e.g. after a
re-upload or a pipeline re-run), which re-runs entity/relationship
extraction. Unique constraints below ensure re-indexing the same
document does not create duplicate entities/relationships/evidence;
the extraction/ingestion service is expected to upsert on these keys.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class GraphEntity(Base):
    """A single extracted entity (person, org, clause, term, etc.).

    ``canonical_name`` is the normalized form (e.g. lowercased/trimmed)
    used for de-duplication within a document; ``name`` preserves the
    original surface form as it appeared in the source text.
    """

    __tablename__ = "graph_entities"
    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "canonical_name",
            "entity_type",
            name="uq_graph_entities_document_canonical_name_type",
        ),
        Index("ix_graph_entities_document_id", "document_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    canonical_name: Mapped[str] = mapped_column(String(500), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    outgoing_relationships: Mapped[list["GraphRelationship"]] = relationship(
        "GraphRelationship",
        back_populates="source_entity",
        foreign_keys="GraphRelationship.source_entity_id",
        cascade="all, delete-orphan",
    )
    incoming_relationships: Mapped[list["GraphRelationship"]] = relationship(
        "GraphRelationship",
        back_populates="target_entity",
        foreign_keys="GraphRelationship.target_entity_id",
        cascade="all, delete-orphan",
    )


class GraphRelationship(Base):
    """A directed edge between two entities extracted from a document."""

    __tablename__ = "graph_relationships"
    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "source_entity_id",
            "target_entity_id",
            "relationship_type",
            name="uq_graph_relationships_document_source_target_type",
        ),
        # Referenced by GraphEvidence's composite FK below -- Postgres
        # requires a unique constraint on the referenced column pair.
        # This is what lets that FK enforce "evidence.document_id must
        # match the document_id of the relationship it points to",
        # not just "relationship_id must exist somewhere".
        UniqueConstraint(
            "id",
            "document_id",
            name="uq_graph_relationships_id_document_id",
        ),
        Index("ix_graph_relationships_document_id", "document_id"),
        Index("ix_graph_relationships_source_entity_id", "source_entity_id"),
        Index("ix_graph_relationships_target_entity_id", "target_entity_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("graph_entities.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("graph_entities.id", ondelete="CASCADE"),
        nullable=False,
    )
    relationship_type: Mapped[str] = mapped_column(String(100), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    source_entity: Mapped["GraphEntity"] = relationship(
        "GraphEntity",
        back_populates="outgoing_relationships",
        foreign_keys=[source_entity_id],
    )
    target_entity: Mapped["GraphEntity"] = relationship(
        "GraphEntity",
        back_populates="incoming_relationships",
        foreign_keys=[target_entity_id],
    )
    evidence: Mapped[list["GraphEvidence"]] = relationship(
        "GraphEvidence",
        back_populates="relationship",
        cascade="all, delete-orphan",
    )


class GraphEvidence(Base):
    """Provenance for a single relationship: the chunk/page/passage it
    was extracted from.

    ``chunk_id`` is a plain string (not a FK) referencing the existing
    HierarchicalChunk/TextNode node_id -- there is no PostgreSQL chunk
    table to reference, since chunks only exist as objects embedded
    into Qdrant.

    ``relationship_id`` + ``document_id`` together are a composite FK
    into ``graph_relationships(id, document_id)`` rather than two
    independent FKs. A single-column FK on ``relationship_id`` alone
    would only guarantee the relationship row exists somewhere -- it
    would happily accept evidence whose ``document_id`` names a
    different document than the relationship it's attached to. The
    composite FK makes that state unrepresentable: Postgres will only
    accept a (relationship_id, document_id) pair that matches an
    actual row in graph_relationships, so evidence can never point at
    a relationship belonging to a different document.
    """

    __tablename__ = "graph_evidence"
    __table_args__ = (
        UniqueConstraint(
            "relationship_id",
            "chunk_id",
            name="uq_graph_evidence_relationship_chunk",
        ),
        ForeignKeyConstraint(
            ["relationship_id", "document_id"],
            ["graph_relationships.id", "graph_relationships.document_id"],
            ondelete="CASCADE",
            name="fk_graph_evidence_relationship_document",
        ),
        Index("ix_graph_evidence_relationship_id", "relationship_id"),
        Index("ix_graph_evidence_document_id", "document_id"),
        Index("ix_graph_evidence_chunk_id", "chunk_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # No column-level ForeignKey() here -- relationship_id is enforced
    # only via the composite ForeignKeyConstraint above, together with
    # document_id.
    relationship_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    chunk_id: Mapped[str] = mapped_column(String(255), nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    relationship: Mapped["GraphRelationship"] = relationship(
        "GraphRelationship", back_populates="evidence"
    )
