"""Unit tests for the online response evaluator."""

from types import SimpleNamespace

import pytest

from app.core.config import Settings
from app.evaluation import response_evaluator as module


class _FakeScorer:
    def __init__(self, result: dict):
        self.result = result

    async def score(self, **kwargs):
        return self.result


def _patch_scorers(monkeypatch, grounding, completeness):
    monkeypatch.setattr(
        module.weave, "init", lambda *args, **kwargs: SimpleNamespace()
    )
    monkeypatch.setattr(
        module,
        "HallucinationFreeScorer",
        lambda **kwargs: grounding,
    )
    monkeypatch.setattr(
        module,
        "CompletenessScorer",
        lambda **kwargs: completeness,
    )


def _settings():
    return Settings(
        RESPONSE_EVALUATION_ENABLED=True,
        WANDB_API_KEY="test",
    )


@pytest.mark.asyncio
async def test_evaluator_passes_grounded_complete_answer(monkeypatch):
    _patch_scorers(
        monkeypatch,
        _FakeScorer({
            "has_hallucination": False,
            "reasonings": "All claims are supported.",
        }),
        _FakeScorer({
            "complete": True,
            "missing_information": [],
            "reasoning": "All requested information is covered.",
        }),
    )

    evaluator = module.ResponseEvaluator(_settings())
    result = await evaluator.evaluate(
        query="How many leave days are allowed?",
        context="Employees receive 20 days of paid annual leave.",
        answer="Employees receive 20 days of paid annual leave.",
    )

    assert result.passed is True
    assert result.has_hallucination is False


@pytest.mark.asyncio
async def test_evaluator_rejects_hallucinated_answer(monkeypatch):
    _patch_scorers(
        monkeypatch,
        _FakeScorer({
            "has_hallucination": True,
            "reasonings": (
                "The answer invents a 30-day entitlement "
                "not present in context."
            ),
        }),
        _FakeScorer({
            "complete": True,
            "missing_information": [],
            "reasoning": "All requested information is covered.",
        }),
    )

    evaluator = module.ResponseEvaluator(_settings())
    result = await evaluator.evaluate(
        query="How many leave days are allowed?",
        context="Employees receive 20 days of paid annual leave.",
        answer="Employees receive 30 days of paid annual leave.",
    )

    assert result.passed is False
    assert result.has_hallucination is True
    assert "30-day" in result.reasoning


@pytest.mark.asyncio
async def test_evaluator_rejects_incomplete_project_atlas_answer(monkeypatch):
    _patch_scorers(
        monkeypatch,
        _FakeScorer({
            "has_hallucination": False,
            "reasonings": "All included claims are supported.",
        }),
        _FakeScorer({
            "complete": False,
            "missing_information": [
                "Go-live date: 30 November 2026"
            ],
            "reasoning": "The answer omits the go-live date.",
        }),
    )

    evaluator = module.ResponseEvaluator(_settings())
    result = await evaluator.evaluate(
        query=(
            "Who is the project owner and technical lead for Project Atlas, "
            "what is the go-live date, and what dependencies must be "
            "completed before UAT?"
        ),
        context=(
            "Project Atlas owner: Priya Sharma. "
            "Technical lead: Arjun Mehta. "
            "Go-live date: 30 November 2026. "
            "Authentication integration must be completed before UAT."
        ),
        answer=(
            "Priya Sharma is the project owner and Arjun Mehta is the "
            "technical lead. Authentication integration must be completed "
            "before UAT."
        ),
    )

    assert result.passed is False
    assert result.has_hallucination is True
    assert "Completeness failure" in result.reasoning
    assert "30 November 2026" in result.reasoning


@pytest.mark.asyncio
async def test_evaluator_rejects_incomplete_result_without_missing_details(
    monkeypatch,
):
    _patch_scorers(
        monkeypatch,
        _FakeScorer({
            "has_hallucination": False,
            "reasonings": "All included claims are supported.",
        }),
        _FakeScorer({
            "complete": False,
            "missing_information": [],
            "reasoning": "Some information may be missing.",
        }),
    )

    evaluator = module.ResponseEvaluator(_settings())

    # The real CompletenessScorer rejects this contradictory result.
    # This test verifies that a scorer exception propagates rather than
    # allowing the answer to pass.
    monkeypatch.setattr(
        evaluator._completeness_scorer,
        "score",
        _raise_invalid_completeness,
    )

    with pytest.raises(ValueError):
        await evaluator.evaluate(
            query="What is the project go-live date?",
            context="Go-live date: 30 November 2026.",
            answer="The project owner is Priya Sharma.",
        )


async def _raise_invalid_completeness(**kwargs):
    raise ValueError("Completeness result is invalid")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_live_completeness_scorer_rejects_missing_go_live_date():
    evaluator = module.ResponseEvaluator(
        Settings(RESPONSE_EVALUATION_ENABLED=True)
    )

    result = await evaluator.evaluate(
        query=(
            "Who is the project owner and technical lead for Project Atlas, "
            "what is the go-live date, and what dependencies must be "
            "completed before UAT?"
        ),
        context=(
            "Project Atlas owner: Priya Sharma. "
            "Technical lead: Arjun Mehta. "
            "Go-live date: 30 November 2026. "
            "Authentication integration must be completed before UAT."
        ),
        answer=(
            "Priya Sharma is the project owner and Arjun Mehta is the "
            "technical lead. Authentication integration must be completed "
            "before UAT."
        ),
    )

    assert result.passed is False, result.reasoning
    assert "completeness" in result.reasoning.lower()
    assert "30 November 2026" in result.reasoning
