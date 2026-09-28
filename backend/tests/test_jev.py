"""Tests for the JEV intent contract."""

import pytest
from pydantic import ValidationError

from app.knowledge_engine.retrieval.adaptive_retrieval_orchestrator import RetrievalMode
from app.knowledge_engine.retrieval.jev import JEVIntent, JEVResult, classify_query


@pytest.mark.parametrize(
    ("intent", "retrieval_mode", "depth"),
    [
        (JEVIntent.FACTUAL_LOOKUP, RetrievalMode.HYBRID, 0),
        (JEVIntent.RELATIONSHIP_LOOKUP, RetrievalMode.GRAPH, 1),
        (JEVIntent.MULTI_HOP, RetrievalMode.HYBRID_GRAPH, 2),
        (JEVIntent.AMBIGUOUS, RetrievalMode.HYBRID, 0),
    ],
)
def test_jev_result_valid_intent_mapping(
    intent: JEVIntent,
    retrieval_mode: RetrievalMode,
    depth: int,
) -> None:
    result = JEVResult(
        intent=intent,
        retrieval_mode=retrieval_mode,
        depth=depth,
    )

    assert result.intent == intent
    assert result.retrieval_mode == retrieval_mode
    assert result.depth == depth


def test_jev_result_rejects_invalid_intent() -> None:
    with pytest.raises(ValidationError):
        JEVResult(
            intent="invalid_intent",
            retrieval_mode=RetrievalMode.HYBRID,
            depth=0,
        )


def test_jev_result_rejects_invalid_retrieval_mode() -> None:
    with pytest.raises(ValidationError):
        JEVResult(
            intent=JEVIntent.FACTUAL_LOOKUP,
            retrieval_mode="invalid_mode",
            depth=0,
        )


def test_jev_result_rejects_negative_depth() -> None:
    with pytest.raises(ValidationError):
        JEVResult(
            intent=JEVIntent.FACTUAL_LOOKUP,
            retrieval_mode=RetrievalMode.HYBRID,
            depth=-1,
        )


def test_jev_result_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        JEVResult(
            intent=JEVIntent.FACTUAL_LOOKUP,
            retrieval_mode=RetrievalMode.HYBRID,
            depth=0,
            unexpected="value",
        )


def test_jev_result_serializes_to_expected_json() -> None:
    result = JEVResult(
        intent=JEVIntent.MULTI_HOP,
        retrieval_mode=RetrievalMode.HYBRID_GRAPH,
        depth=2,
    )

    assert result.model_dump(mode="json") == {
        "intent": "multi_hop",
        "retrieval_mode": "hybrid_graph",
        "depth": 2,
    }


def test_classify_factual_lookup():
    result = classify_query("What is the travel expense policy?")
    assert result.intent == JEVIntent.FACTUAL_LOOKUP
    assert result.retrieval_mode == RetrievalMode.HYBRID
    assert result.depth == 0


def test_classify_relationship_lookup():
    result = classify_query("What is the relationship between Finance and Procurement?")
    assert result.intent == JEVIntent.RELATIONSHIP_LOOKUP
    assert result.retrieval_mode == RetrievalMode.GRAPH
    assert result.depth == 1


def test_classify_multi_hop():
    result = classify_query(
        "What happens downstream after the procurement approval and then the finance review?"
    )
    assert result.intent == JEVIntent.MULTI_HOP
    assert result.retrieval_mode == RetrievalMode.HYBRID_GRAPH
    assert result.depth == 2


def test_classify_multi_hop_takes_precedence():
    result = classify_query(
        "What is the relationship between procurement and finance and then what happens downstream?"
    )
    assert result.intent == JEVIntent.MULTI_HOP
    assert result.retrieval_mode == RetrievalMode.HYBRID_GRAPH
    assert result.depth == 2
