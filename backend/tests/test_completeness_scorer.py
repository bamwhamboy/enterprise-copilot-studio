"""Unit tests for the dedicated completeness scorer."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.evaluation.completeness_scorer import CompletenessScorer


@pytest.fixture
def scorer():
    instance = CompletenessScorer(model_id="groq/openai/gpt-oss-20b")
    instance._acompletion = AsyncMock()
    return instance


def _response(content):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content)
            )
        ]
    )


@pytest.mark.asyncio
async def test_accepts_complete_answer(scorer):
    scorer._acompletion.return_value = _response(
        '{"complete": true, "missing_information": [], '
        '"reasoning": "All requested facts are covered."}'
    )

    result = await scorer.score(
        context="Question: What is the go-live date? "
               "Retrieved context: Go-live date: 30 November 2026.",
        output="The go-live date is 30 November 2026.",
    )

    assert result["complete"] is True
    assert result["missing_information"] == []


@pytest.mark.asyncio
async def test_accepts_incomplete_answer(scorer):
    scorer._acompletion.return_value = _response(
        '{"complete": false, '
        '"missing_information": ["Go-live date: 30 November 2026"], '
        '"reasoning": "The answer omits the go-live date."}'
    )

    result = await scorer.score(
        context="Go-live date: 30 November 2026.",
        output="The project owner is Priya Sharma.",
    )

    assert result["complete"] is False
    assert "30 November 2026" in result["missing_information"][0]


@pytest.mark.asyncio
async def test_rejects_contradictory_complete_result(scorer):
    scorer._acompletion.return_value = _response(
        '{"complete": true, '
        '"missing_information": ["Go-live date"], '
        '"reasoning": "A date is missing."}'
    )

    with pytest.raises(ValueError, match="contradictory"):
        await scorer.score(context="Some context", output="Some answer")


@pytest.mark.asyncio
async def test_rejects_incomplete_result_without_missing_details(scorer):
    scorer._acompletion.return_value = _response(
        '{"complete": false, "missing_information": [], '
        '"reasoning": "Something is missing."}'
    )

    with pytest.raises(ValueError, match="without identifying"):
        await scorer.score(context="Some context", output="Some answer")


@pytest.mark.asyncio
async def test_rejects_malformed_json(scorer):
    scorer._acompletion.return_value = _response(
        "This is not valid JSON"
    )

    with pytest.raises(ValueError):
        await scorer.score(context="Some context", output="Some answer")


@pytest.mark.asyncio
async def test_rejects_empty_response(scorer):
    scorer._acompletion.return_value = _response(None)

    with pytest.raises(ValueError, match="empty response"):
        await scorer.score(context="Some context", output="Some answer")


@pytest.mark.asyncio
async def test_rejects_unexpected_fields(scorer):
    scorer._acompletion.return_value = _response(
        '{"complete": true, "missing_information": [], '
        '"reasoning": "Complete.", "extra": "unexpected"}'
    )

    with pytest.raises(ValueError):
        await scorer.score(context="Some context", output="Some answer")


@pytest.mark.asyncio
async def test_uses_json_object_mode_and_zero_temperature(scorer):
    scorer._acompletion.return_value = _response(
        '{"complete": true, "missing_information": [], '
        '"reasoning": "Complete."}'
    )

    await scorer.score(context="Context", output="Answer")

    call = scorer._acompletion.await_args.kwargs

    assert call["response_format"] == {"type": "json_object"}
    assert call["temperature"] == 0.0
    assert call["model"] == "groq/openai/gpt-oss-20b"
