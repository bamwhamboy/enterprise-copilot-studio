"""Shapes for one chunk's graph extraction, mirroring the style of
``app/llm/models.py`` -- these describe the *shape* of what the LLM
is asked to return, not persistence (see ``app/models/graph.py`` for
the ORM models these get resolved into).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ExtractedEntity(BaseModel):
    """One entity as extracted from a single chunk's text."""

    name: str
    canonical_name: str
    entity_type: str


class ExtractedRelationship(BaseModel):
    """One relationship as extracted from a single chunk's text.

    ``source_entity``/``target_entity`` are ``canonical_name`` values
    that must match an entity in the same chunk's ``entities`` list --
    the LLM has no notion of database identity, only what's referenced
    within the current instructions. Resolving these strings to actual
    ``GraphEntity`` rows (including entities from *other* chunks in the
    same document) is ``GraphExtractionService``'s job, not the
    extractor's.
    """

    source_entity: str
    target_entity: str
    relationship_type: str
    confidence: float = Field(ge=0.0, le=1.0)


class ChunkExtractionResult(BaseModel):
    """Everything extracted from one chunk, before entity resolution."""

    entities: list[ExtractedEntity] = Field(default_factory=list)
    relationships: list[ExtractedRelationship] = Field(default_factory=list)
