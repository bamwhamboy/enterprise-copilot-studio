"""Re-ranking.

Re-scores an already-retrieved (RRF-fused) chunk list using a lexical
term-overlap signal against the query, blended with the existing
retrieval score. This is a lightweight, dependency-free re-ranking
stage -- not a cross-encoder -- chosen deliberately so it needs no
model download and runs in this (network-restricted) environment.
Swappable later for a real cross-encoder re-ranker behind the same
interface.

Explicitly does NOT replace HybridRetriever -- it's a post-processing
step over its output.
"""

from __future__ import annotations

import re

from app.knowledge_engine.models import RetrievedChunk

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> set:
    return set(_TOKEN_RE.findall(text.lower()))


class Reranker:
    """Blends the original retrieval score with a lexical overlap boost."""

    def __init__(self, *, overlap_weight: float = 0.3) -> None:
        self._overlap_weight = overlap_weight

    def rerank(self, query: str, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        if not chunks:
            return chunks

        query_terms = _tokenize(query)
        max_score = max((c.score for c in chunks), default=1.0) or 1.0

        rescored: list[RetrievedChunk] = []
        for chunk in chunks:
            overlap = len(query_terms & _tokenize(chunk.text))
            overlap_ratio = overlap / len(query_terms) if query_terms else 0.0
            normalized_original = chunk.score / max_score
            blended = (
                1 - self._overlap_weight
            ) * normalized_original + self._overlap_weight * overlap_ratio
            rescored.append(chunk.model_copy(update={"score": blended}))

        return sorted(rescored, key=lambda c: c.score, reverse=True)
