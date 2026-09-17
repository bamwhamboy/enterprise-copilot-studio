"""Pydantic schemas for Copilot."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import ORMBaseModel
from app.schemas.knowledge_source import KnowledgeSourceSummary

# Domains are configurable/free-form (Sprint 1) rather than a fixed
# set -- this alias exists only for readability in type annotations
# below, not to restrict values. Validation/normalization lives in
# _normalize_domain, applied via a field_validator on both
# CopilotCreate and CopilotUpdate.
CopilotDomain = str
CopilotStatus = Literal["draft", "active", "archived"]

# The real business-rule bound (<=100 chars) is enforced in
# _normalize_domain against the *normalized* value, matching the
# database column's actual capacity (String(100)). The generous
# Field-level max_length below is only a defensive guard against
# processing an absurdly large raw payload before normalization runs.
_DOMAIN_MAX_LENGTH = 100
_DOMAIN_RAW_MAX_LENGTH = 500


def _normalize_domain(value: str) -> str:
    """Strip, lowercase, and validate a copilot domain.

    Applied identically wherever a domain is accepted as input
    (CopilotCreate, CopilotUpdate) so "Clinical Research" and
    "clinical research" and "  Clinical Research  " all normalize to
    the same stored value: "clinical research".
    """
    normalized = value.strip().lower()
    if not normalized:
        raise ValueError("domain must not be empty or whitespace-only")
    if len(normalized) > _DOMAIN_MAX_LENGTH:
        raise ValueError(f"domain must be at most {_DOMAIN_MAX_LENGTH} characters")
    return normalized


class CopilotCreate(BaseModel):
    """Payload for ``POST /api/v1/copilots``."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    # Free-form domain (Sprint 1: Configurable Copilot Domains) --
    # "hr" preserved as the default for backward compatibility with
    # existing callers that don't specify one.
    domain: str = Field(default="hr", max_length=_DOMAIN_RAW_MAX_LENGTH)
    status: CopilotStatus = "draft"
    # Kept in sync with Settings.DEFAULT_LLM_MODEL (app/core/config.py) --
    # this is the value actually persisted for API-created copilots that
    # don't specify their own model (the ORM column's own default is
    # never reached, since the service always passes this field through
    # explicitly).
    model: str = Field(default="openai/gpt-oss-120b", max_length=100)
    knowledge_source_ids: list[uuid.UUID] = Field(default_factory=list)

    @field_validator("domain")
    @classmethod
    def _validate_domain(cls, value: str) -> str:
        return _normalize_domain(value)


class CopilotUpdate(BaseModel):
    """Payload for ``PUT /api/v1/copilots/{id}``. All fields optional.

    When ``knowledge_source_ids`` is provided, it replaces the copilot's
    full set of linked knowledge sources.
    """

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    domain: str | None = Field(default=None, max_length=_DOMAIN_RAW_MAX_LENGTH)
    status: CopilotStatus | None = None
    model: str | None = Field(default=None, max_length=100)
    knowledge_source_ids: list[uuid.UUID] | None = None

    @field_validator("domain")
    @classmethod
    def _validate_domain(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _normalize_domain(value)


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
