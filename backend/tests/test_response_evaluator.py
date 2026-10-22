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


@pytest.mark.asyncio
async def test_evaluator_passes_grounded_answer(monkeypatch):
    scorer = _FakeScorer(
        {"has_hallucination": False, "reasonings": "All claims are supported."}
    )
    monkeypatch.setattr(module.weave, "init", lambda *args, **kwargs: SimpleNamespace())
    monkeypatch.setattr(module, "HallucinationFreeScorer", lambda **kwargs: scorer)

    evaluator = module.ResponseEvaluator(
        Settings(RESPONSE_EVALUATION_ENABLED=True, WANDB_API_KEY="test")
    )
    result = await evaluator.evaluate(
        query="How many leave days are allowed?",
        context="Employees receive 20 days of paid annual leave.",
        answer="Employees receive 20 days of paid annual leave.",
    )

    assert result.passed is True
    assert result.has_hallucination is False
    assert result.reasoning == "All claims are supported."


@pytest.mark.asyncio
async def test_evaluator_rejects_hallucinated_answer(monkeypatch):
    scorer = _FakeScorer(
        {
            "has_hallucination": True,
            "reasonings": "The answer invents a 30-day entitlement not present in context.",
        }
    )
    monkeypatch.setattr(module.weave, "init", lambda *args, **kwargs: SimpleNamespace())
    monkeypatch.setattr(module, "HallucinationFreeScorer", lambda **kwargs: scorer)

    evaluator = module.ResponseEvaluator(
        Settings(RESPONSE_EVALUATION_ENABLED=True, WANDB_API_KEY="test")
    )
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
    grounding_scorer = _FakeScorer(
        {
            "has_hallucination": False,
            "reasonings": "All included claims are supported.",
        }
    )
    completeness_scorer = _FakeScorer(
        {
            "has_hallucination": True,
            "reasonings": (
                "Incomplete: the go-live date, 30 November 2026, "
                "is present in the context but missing from the answer."
            ),
        }
    )

    scorers = iter([grounding_scorer, completeness_scorer])

    monkeypatch.setattr(
        module.weave, "init", lambda *args, **kwargs: SimpleNamespace()
    )
    monkeypatch.setattr(
        module,
        "HallucinationFreeScorer",
        lambda **kwargs: next(scorers),
    )

    evaluator = module.ResponseEvaluator(
        Settings(RESPONSE_EVALUATION_ENABLED=True, WANDB_API_KEY="test")
    )

    result = await evaluator.evaluate(
        query=(
            "Who is the project owner and technical lead for Project Atlas, "
            "what is the go-live date, and what dependencies must be completed before UAT?"
        ),
        context=(
            "Project Atlas owner: Priya Sharma. "
            "Technical lead: Arjun Mehta. "
            "Go-live date: 30 November 2026. "
            "Authentication integration must be completed before UAT."
        ),
        answer=(
            "Priya Sharma is the project owner and Arjun Mehta is the technical lead. "
            "Authentication integration must be completed before UAT."
        ),
    )

    assert result.passed is False
    assert result.has_hallucination is True
    assert "go-live date" in result.reasoning

@pytest.mark.asyncio
@pytest.mark.integration
async def test_live_completeness_scorer_rejects_missing_go_live_date():
    settings = Settings(RESPONSE_EVALUATION_ENABLED=True)
    evaluator = module.ResponseEvaluator(settings)

    result = await evaluator.evaluate(
        query=(
            "Who is the project owner and technical lead for Project Atlas, "
            "what is the go-live date, and what dependencies must be completed before UAT?"
        ),
        context=(
            "Project Atlas owner: Priya Sharma. "
            "Technical lead: Arjun Mehta. "
            "Go-live date: 30 November 2026. "
            "Authentication integration must be completed before UAT."
        ),
        answer=(
            "Priya Sharma is the project owner and Arjun Mehta is the technical lead. "
            "Authentication integration must be completed before UAT."
        ),
    )

    assert result.passed is False, result.reasoning
    assert "completeness" in result.reasoning.lower(), result.reasoning
