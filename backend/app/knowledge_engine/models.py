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
