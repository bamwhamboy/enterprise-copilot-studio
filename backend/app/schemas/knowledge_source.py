"""Pydantic schemas for KnowledgeSource."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import ORMBaseModel
from app.schemas.document import DocumentRead

KnowledgeSourceType = Literal["documents", "database", "website", "connector"]
KnowledgeSourceStatus = Literal["active", "syncing", "connected", "pending", "coming_soon"]


class KnowledgeSourceCreate(BaseModel):
    """Payload for ``POST /api/v1/knowledge-sources``."""

    name: str = Field(min_length=1, max_length=255)
    source_type: KnowledgeSourceType = "documents"
    status: KnowledgeSourceStatus = "active"


class KnowledgeSourceUpdate(BaseModel):
    """Payload for ``PUT /api/v1/knowledge-sources/{id}``. All fields optional."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    source_type: KnowledgeSourceType | None = None
    status: KnowledgeSourceStatus | None = None


class KnowledgeSourceSummary(ORMBaseModel):
    """Lightweight representation used when embedded inside a Copilot response."""

    id: uuid.UUID
    name: str
    source_type: KnowledgeSourceType
    status: KnowledgeSourceStatus


class KnowledgeSourceRead(ORMBaseModel):
    """Full response schema for a KnowledgeSource, including its documents."""

    id: uuid.UUID
    name: str
    source_type: KnowledgeSourceType
    status: KnowledgeSourceStatus
    created_at: datetime
    updated_at: datetime
    documents: list[DocumentRead] = Field(default_factory=list)
