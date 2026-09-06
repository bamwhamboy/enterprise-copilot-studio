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
