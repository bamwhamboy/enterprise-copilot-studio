"""Pydantic schemas for Document."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import ORMBaseModel

DocumentStatus = Literal["pending", "processing", "indexed"]
ProcessingStatus = Literal["UPLOADED", "PROCESSING", "READY", "FAILED"]
IndexStatus = Literal["NOT_INDEXED", "INDEXING", "INDEXED", "FAILED"]


class DocumentCreate(BaseModel):
    """Payload for ``POST /api/v1/documents`` (JSON, no file — unchanged from Sprint 2)."""

    knowledge_source_id: uuid.UUID
    name: str = Field(min_length=1, max_length=255)
    status: DocumentStatus = "pending"
    pages: int = Field(default=0, ge=0)
    chunks: int = Field(default=0, ge=0)
    embeddings: int = Field(default=0, ge=0)


class DocumentRead(ORMBaseModel):
    """Response schema for a Document.

    The Sprint 3A fields are ``None`` for documents created via the
    Sprint 2 JSON endpoint (no file involved) and populated for
    documents created via ``POST /documents/upload``.
    """

    id: uuid.UUID
    knowledge_source_id: uuid.UUID
    name: str
    status: DocumentStatus
    pages: int
    chunks: int
    embeddings: int
    original_filename: str | None = None
    storage_path: str | None = None
    extracted_text_path: str | None = None
    mime_type: str | None = None
    file_size_bytes: int | None = None
    processing_status: ProcessingStatus | None = None
    index_status: IndexStatus | None = None
    created_at: datetime
    updated_at: datetime
