"""Shared data models for the Enterprise Retrieval Engine.

Strongly-typed shapes used across chunking, indexing, retrieval, and
citations — analogous to ``app/llm/models.py`` in Sprint 4.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field


class ChunkMetadata(BaseModel):
    """Metadata attached to every chunk, per Sprint 3B's required fields."""

    document_id: str
    knowledge_source_id: str
    document_name: str
    page_number: int | None = None
    section: str | None = None
    subsection: str | None = None
    chunk_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    chunk_number: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class HierarchicalChunk(BaseModel):
    """A single chunk produced by hierarchical chunking, with its text and metadata."""

    text: str
    metadata: ChunkMetadata
    parent_chunk_id: str | None = None
    node_id: str  # underlying LlamaIndex node id, for parent/child traversal


class Citation(BaseModel):
    """What a retrieved chunk exposes to a (future) copilot response."""

    # Stable identity (Document.id, as stored in Qdrant under the
    # "source_document_id" payload key -- see citation_builder.py). Kept
    # alongside document_name (a mutable display label, not a safe
    # identity key) rather than replacing it: citations need both a
    # human-readable name and a stable id two documents can never
    # collide on, even if identically named. Defaults to "" (same
    # fallback style as knowledge_source_id below) rather than being
    # required, so existing callers that predate this field -- direct
    # Citation(...) construction elsewhere in the codebase, not just
    # build_citation() -- keep working unmodified; build_citation()
    # itself always populates the real value explicitly.
    document_id: str = ""
    document_name: str
    knowledge_source_id: str
    page_number: int | None = None
    section: str | None = None
    chunk_number: int
    score: float | None = None


class RetrievedChunk(BaseModel):
    """A chunk returned by retrieval, with its score and citation."""

    text: str
    score: float
    citation: Citation
    chunk_id: str
