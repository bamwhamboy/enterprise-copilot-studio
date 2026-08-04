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
    """A single indexed (or pending) document within a knowledge source."""

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
    # "pending" | "processing" | "indexed"
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    pages: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    chunks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    embeddings: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

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
