"""Document ORM model.

A Document belongs to exactly one KnowledgeSource (one-to-many). Deleting
a KnowledgeSource cascades to delete its Documents.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Document(Base):
    """A single indexed (or pending) document within a knowledge source.

    Sprint 3A adds the ingestion-pipeline fields below. They're all
    nullable since Sprint 2's JSON-only ``POST /documents`` path (still
    supported, unchanged) never populates them — only documents created
    via ``POST /documents/upload`` do.
    """

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    knowledge_source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_sources.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # "pending" | "processing" | "indexed" — Sprint 2's coarse status, kept
    # as-is for backward compatibility. Synced to "indexed" once the
    # Sprint 3A ingestion pipeline reaches processing_status="READY".
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    pages: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    chunks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    embeddings: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # --- Sprint 3A: ingestion pipeline fields --------------------------------
    original_filename: Mapped[str | None] = mapped_column(String(500), nullable=True)
    storage_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    extracted_text_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(150), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # "UPLOADED" | "PROCESSING" | "READY" | "FAILED"; None for documents
    # created via the Sprint 2 JSON endpoint (no file involved).
    processing_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # Sprint 3B: "NOT_INDEXED" | "INDEXING" | "INDEXED" | "FAILED" — tracks
    # the RAG indexing pipeline, distinct from the ingestion pipeline above.
    # A document can be READY (parsed) but NOT_INDEXED (not yet embedded).
    index_status: Mapped[str | None] = mapped_column(String(50), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    knowledge_source: Mapped["KnowledgeSource"] = relationship(
        "KnowledgeSource", back_populates="documents"
    )
