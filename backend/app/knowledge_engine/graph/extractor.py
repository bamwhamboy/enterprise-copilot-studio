"""Per-chunk entity/relationship extraction via the existing LLM gateway.

Deliberately thin: this module's only job is "chunk text in, parsed
``ChunkExtractionResult`` out (or raise)". Entity resolution across
chunks, persistence, provenance, and per-chunk failure isolation all
live in ``graph_extraction_service.py`` -- this module has no
knowledge of the database.
"""

from __future__ import annotations

import json
import re

from pydantic import ValidationError

from app.core.logging import get_logger
from app.knowledge_engine.graph.models import ChunkExtractionResult
from app.llm.gateway import LLMGateway
from app.llm.models import GenerationRequest, LLMMessage

logger = get_logger(__name__)

_SYSTEM_PROMPT = """You are an information-extraction engine for an enterprise \
knowledge graph. Given a single chunk of text from a business document, extract:

1. entities: distinct people, organizations, defined terms, monetary amounts, \
dates, or clauses that matter for understanding the document.
2. relationships: directed relationships between two of the entities you extracted.

Respond with ONLY a single JSON object, no markdown fences, no commentary, in \
exactly this shape:

{
  "entities": [
    {"name": "<surface form as it appears in the text>", \
"canonical_name": "<normalized/lowercased form>", "entity_type": "<short type, \
e.g. organization, person, term, amount, date, clause>"}
  ],
  "relationships": [
    {"source_entity": "<canonical_name of an entity above>", \
"target_entity": "<canonical_name of a different entity above>", \
"relationship_type": "<short snake_case predicate, e.g. provides_services_to>", \
"confidence": <float between 0.0 and 1.0>}
  ]
}

Every "source_entity"/"target_entity" value MUST exactly match a "canonical_name" \
already present in "entities". If the chunk contains no meaningful entities or \
relationships, return {"entities": [], "relationships": []}."""

_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)


class GraphExtractionError(Exception):
    """Raised when the LLM response cannot be parsed into a valid
    ``ChunkExtractionResult`` -- covers both malformed JSON and JSON
    that doesn't match the expected schema."""


class GraphExtractor:
    """Extracts entities and relationships from one chunk of text at a time."""

    def __init__(self, gateway: LLMGateway) -> None:
        # No Settings needed here: the gateway already resolves
        # provider/model from Settings.DEFAULT_LLM_PROVIDER /
        # Settings.DEFAULT_LLM_MODEL when a request omits them (see
        # LLMGateway._resolve_provider) -- passing None below reuses
        # that existing configuration instead of introducing a new one.
        self._gateway = gateway

    async def extract(self, chunk_text: str) -> ChunkExtractionResult:
        """Extract entities/relationships from a single chunk's text.

        Raises ``GraphExtractionError`` if the LLM's response cannot be
        parsed -- callers (``GraphExtractionService``) are expected to
        catch this per chunk rather than let it abort the whole document.
        """
        request = GenerationRequest(
            messages=[
                LLMMessage(role="system", content=_SYSTEM_PROMPT),
                LLMMessage(role="user", content=chunk_text),
            ],
            # Deterministic, low-temperature extraction -- this is a
            # structured-data task, not a creative one.
            temperature=0.0,
        )
        response = await self._gateway.generate(request)
        return self._parse(response.content)

    def _parse(self, raw_content: str) -> ChunkExtractionResult:
        cleaned = _JSON_FENCE_RE.sub("", raw_content.strip()).strip()

        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise GraphExtractionError(
                f"LLM response was not valid JSON: {exc}"
            ) from exc

        try:
            result = ChunkExtractionResult.model_validate(payload)
        except ValidationError as exc:
            raise GraphExtractionError(
                f"LLM response did not match the expected extraction schema: {exc}"
            ) from exc

        known_canonical_names = {entity.canonical_name for entity in result.entities}
        valid_relationships = []
        for relationship in result.relationships:
            if (
                relationship.source_entity not in known_canonical_names
                or relationship.target_entity not in known_canonical_names
            ):
                logger.warning(
                    "Dropping relationship referencing unknown entity "
                    "(source=%r target=%r); not present in this chunk's "
                    "extracted entities",
                    relationship.source_entity,
                    relationship.target_entity,
                )
                continue
            valid_relationships.append(relationship)

        return ChunkExtractionResult(
            entities=result.entities, relationships=valid_relationships
        )
