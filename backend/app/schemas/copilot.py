"""Pydantic schemas for Copilot."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import ORMBaseModel
from app.schemas.knowledge_source import KnowledgeSourceSummary

CopilotDomain = Literal["hr", "finance", "procurement", "sales", "legal", "it", "analytics"]
CopilotStatus = Literal["draft", "active", "archived"]


class CopilotCreate(BaseModel):
    """Payload for ``POST /api/v1/copilots``."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    domain: CopilotDomain = "hr"
    status: CopilotStatus = "draft"
    model: str = Field(default="groq-llama-3", max_length=100)
    knowledge_source_ids: list[uuid.UUID] = Field(default_factory=list)


class CopilotUpdate(BaseModel):
    """Payload for ``PUT /api/v1/copilots/{id}``. All fields optional.

    When ``knowledge_source_ids`` is provided, it replaces the copilot's
    full set of linked knowledge sources.
    """

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    domain: CopilotDomain | None = None
    status: CopilotStatus | None = None
    model: str | None = Field(default=None, max_length=100)
    knowledge_source_ids: list[uuid.UUID] | None = None


class CopilotRead(ORMBaseModel):
    """Response schema for a Copilot."""

    id: uuid.UUID
    name: str
    description: str | None
    domain: CopilotDomain
    status: CopilotStatus
    model: str
    created_at: datetime
    updated_at: datetime
    knowledge_sources: list[KnowledgeSourceSummary] = Field(default_factory=list)
