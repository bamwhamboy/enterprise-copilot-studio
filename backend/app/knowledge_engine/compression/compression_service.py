"""Context compression.

Reduces a set of retrieved chunks to a smaller, LLM-ready context: keep
only the top-N highest-scoring chunks, and cap each chunk's text length.
Every chunk's citation is preserved untouched — compression only ever
shortens *text*, never metadata.

Deterministic and dependency-free — no LLM calls, no summarization.
"""

from __future__ import annotations

from app.core.config import Settings
from app.core.logging import get_logger
from app.knowledge_engine.models import RetrievedChunk

logger = get_logger(__name__)


class ContextCompressionService:
    """Reusable, stateless compression over a list of retrieved chunks."""

    def __init__(self, settings: Settings) -> None:
        self._max_chunks = settings.CONTEXT_COMPRESSION_MAX_CHUNKS
        self._max_chars_per_chunk = settings.CONTEXT_COMPRESSION_MAX_CHARS_PER_CHUNK

    def compress(self, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        """Select the top-scoring chunks and truncate each chunk's text.

        Chunks are assumed to already be ranked (highest score first) —
        this is a reduction step, not a re-ranking step.
        """
        selected = chunks[: self._max_chunks]

        compressed = [
            chunk
            if len(chunk.text) <= self._max_chars_per_chunk
            else chunk.model_copy(
                update={"text": chunk.text[: self._max_chars_per_chunk].rstrip() + "…"}
            )
            for chunk in selected
        ]

        logger.info(
            "Compressed %d retrieved chunks to %d (max_chars_per_chunk=%d)",
            len(chunks),
            len(compressed),
            self._max_chars_per_chunk,
        )
        return compressed
