"""Query rewriting.

Default: deterministic normalization (whitespace/punctuation cleanup,
common abbreviation expansion) -- no LLM call, always available.

Optional: LLM-based rewriting via the existing LLM Gateway (Sprint 4),
gated behind Settings.RAG_QUERY_REWRITE_ENABLED and only used when a
gateway is supplied -- this keeps the default retrieval path fast and
dependency-free while making richer rewriting a drop-in upgrade.
"""

from __future__ import annotations

import re

from app.core.logging import get_logger
from app.llm.gateway import LLMGateway
from app.llm.models import GenerationRequest, LLMMessage

logger = get_logger(__name__)

_WHITESPACE_RE = re.compile(r"\s+")

# Small, illustrative set of common workplace-document abbreviations.
# A real deployment would source this from configuration, not hardcode it.
_EXPANSIONS: dict[str, str] = {
    r"\bpto\b": "paid time off",
    r"\bhr\b": "human resources",
    r"\bwfh\b": "work from home",
}


class QueryRewriter:
    """Rewrites a raw user query into a retrieval-friendly search query."""

    def rewrite(self, query: str) -> str:
        """Deterministic rewrite: normalize whitespace and expand abbreviations."""
        text = _WHITESPACE_RE.sub(" ", query).strip()
        for pattern, expansion in _EXPANSIONS.items():
            text = re.sub(pattern, expansion, text, flags=re.IGNORECASE)
        return text

    async def rewrite_with_llm(self, query: str, gateway: LLMGateway) -> str:
        """Optional LLM-based rewrite: expand the query for better recall.

        Falls back to the deterministic rewrite on any failure (e.g. no
        provider configured) -- query rewriting should never be the
        reason a search request fails.
        """
        try:
            request = GenerationRequest(
                messages=[
                    LLMMessage(
                        role="system",
                        content=(
                            "Rewrite the user's question into a concise search "
                            "query optimized for document retrieval. Return only "
                            "the rewritten query, nothing else."
                        ),
                    ),
                    LLMMessage(role="user", content=query),
                ],
                temperature=0.0,
                max_tokens=64,
            )
            response = await gateway.generate(request)
            rewritten = response.content.strip()
            return rewritten or self.rewrite(query)
        except Exception as exc:
            logger.warning("LLM query rewrite failed, falling back to rule-based: %s", exc)
            return self.rewrite(query)
