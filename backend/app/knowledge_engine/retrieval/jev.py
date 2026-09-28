"""JEV intent contract for Enterprise Copilot V2."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.knowledge_engine.retrieval.contracts import RetrievalMode


class JEVIntent(str, Enum):
    """Initial V2 query-intent categories."""

    FACTUAL_LOOKUP = "factual_lookup"
    RELATIONSHIP_LOOKUP = "relationship_lookup"
    MULTI_HOP = "multi_hop"
    AMBIGUOUS = "ambiguous"


class JEVResult(BaseModel):
    """Structured output produced by the JEV intent layer."""

    model_config = ConfigDict(extra="forbid")

    intent: JEVIntent
    retrieval_mode: RetrievalMode
    depth: int = Field(ge=0)

_MULTI_HOP_PATTERNS = (
    "and then",
    "which in turn",
    "eventually",
    "downstream",
    "indirectly",
    "chain of",
    "path from",
    "multi-step",
    "multiple steps",
    "ultimately",
    "as a result of",
    "through which",
    "leads to",
)

_RELATIONSHIP_PATTERNS = (
    "relationship between",
    "relationship with",
    "related to",
    "relation to",
    "connected to",
    "connection between",
    "associated with",
    "linked to",
    "affiliated with",
    "who is",
    "what is the link",
)
def classify_query(query: str) -> JEVResult:
    """Classify a query into an initial V2 retrieval intent."""

    text = query.lower()

    if any(pattern in text for pattern in _MULTI_HOP_PATTERNS):
        return JEVResult(
            intent=JEVIntent.MULTI_HOP,
            retrieval_mode=RetrievalMode.HYBRID_GRAPH,
            depth=2,
        )

    if any(pattern in text for pattern in _RELATIONSHIP_PATTERNS):
        return JEVResult(
            intent=JEVIntent.RELATIONSHIP_LOOKUP,
            retrieval_mode=RetrievalMode.GRAPH,
            depth=1,
        )

    return JEVResult(
        intent=JEVIntent.FACTUAL_LOOKUP,
        retrieval_mode=RetrievalMode.HYBRID,
        depth=0,
    )
