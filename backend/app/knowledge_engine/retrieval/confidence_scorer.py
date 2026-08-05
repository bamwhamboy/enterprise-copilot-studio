"""Confidence scoring.

Derives a single 0-1 confidence value for a retrieval result set, so
the chat orchestrator/response can signal "this answer is well-
grounded" vs. "the retrieved context was weak." Two simple, transparent
signals, averaged:

- absolute strength of the top result's score
- separation between the top result and the rest (a big gap means the
  top result is a clear winner; a flat distribution means low confidence)
"""

from __future__ import annotations

from app.knowledge_engine.models import RetrievedChunk


class ConfidenceScorer:
    def score(self, chunks: list[RetrievedChunk]) -> float:
        if not chunks:
            return 0.0

        scores = sorted((c.score for c in chunks), reverse=True)
        top = scores[0]
        top_strength = max(0.0, min(1.0, top))

        if len(scores) == 1:
            gap_signal = top_strength
        else:
            second = scores[1]
            gap = top - second
            gap_signal = max(0.0, min(1.0, gap / top)) if top > 0 else 0.0

        return round((top_strength + gap_signal) / 2, 4)
