"""KnowledgeSource ORM model.

Represents a single source of knowledge (a document collection, a
database connection, a website, or an enterprise connector) that can
back one or more copilots.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.copilot import copilot_knowledge_sources


class KnowledgeSource(Base):
    """A named source of knowledge documents (e.g. "HR Policies")."""

    __tablename__ = "knowledge_sources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # "documents" | "database" | "website" | "connector"
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, default="documents")
    # "active" | "syncing" | "connected" | "pending" | "coming_soon"
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    copilots: Mapped[list["Copilot"]] = relationship(
        "Copilot",
        secondary=copilot_knowledge_sources,
        back_populates="knowledge_sources",
    )
    documents: Mapped[list["Document"]] = relationship(
        "Document",
        back_populates="knowledge_source",
        cascade="all, delete-orphan",
    )
