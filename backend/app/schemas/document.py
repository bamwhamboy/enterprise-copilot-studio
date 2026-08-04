"""Pydantic schemas for Document."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import ORMBaseModel

DocumentStatus = Literal["pending", "processing", "indexed"]


class DocumentCreate(BaseModel):
    """Payload for ``POST /api/v1/documents``."""

    knowledge_source_id: uuid.UUID
    name: str = Field(min_length=1, max_length=255)
    status: DocumentStatus = "pending"
    pages: int = Field(default=0, ge=0)
    chunks: int = Field(default=0, ge=0)
    embeddings: int = Field(default=0, ge=0)


class DocumentRead(ORMBaseModel):
    """Response schema for a Document."""

    id: uuid.UUID
    knowledge_source_id: uuid.UUID
    name: str
    status: DocumentStatus
    pages: int
    chunks: int
    embeddings: int
    created_at: datetime
    updated_at: datetime
