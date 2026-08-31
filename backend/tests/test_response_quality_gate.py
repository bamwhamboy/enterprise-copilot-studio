"""Tests for the shared response quality gate.

These tests exercise the online evaluator loop without calling a real LLM or
W&B. They prove that an unchecked draft is never emitted, that one failed
evaluation triggers a correction attempt, and that a second failure escalates
to human review.
"""


import pytest

from app.agents import response_generator_node as module
from app.core.config import Settings
from app.evaluation.response_evaluator import ResponseEvaluation
from app.llm.models import LLMMessage

class _FakeGeneration:
    def __init__(self, content: str):
        self.content = content


class _FakeGateway:
    def __init__(self, responses: list[str]):
        self.responses = iter(responses)
        self.requests = []

    async def generate(self, request):
        self.requests.append(request)
        return _FakeGeneration(next(self.responses))


class _FakeGuardrails:
    def enforce_output(self, content: str) -> str:
        return content


class _FakeEvaluator:
    def __init__(self, results: list[ResponseEvaluation]):
        self.results = iter(results)
        self.calls = []

    async def evaluate(self, **kwargs):
        self.calls.append(kwargs)
        return next(self.results)


@pytest.fixture
def settings():
    return Settings(
        RESPONSE_EVALUATION_ENABLED=True,
        RESPONSE_MAX_EVALUATION_ATTEMPTS=2,
        DEFAULT_TEMPERATURE=0.2,
        DEFAULT_MAX_TOKENS=256,
    )


@pytest.fixture(autouse=True)
def fake_stream_writer(monkeypatch):
    emitted = []
    monkeypatch.setattr(module, "get_stream_writer", lambda: lambda event: emitted.append(event))
    return emitted


def _state():
    return {
        "user_message": "What is the reimbursement limit?",
        "copilot_name": "Finance Copilot",
        "domain": "finance",
        "copilot_model": "groq/openai/gpt-oss-20b",
        "llm_messages": [
            LLMMessage(role="system", content="Answer only from the supplied policy."),
	    LLMMessage(role="user", content="What is the reimbursement limit?"),
        ],
        "retrieved_chunks": [],
    }


@pytest.mark.asyncio
async def test_grounded_first_answer_is_emitted(settings, fake_stream_writer):
    gateway = _FakeGateway(["The policy allows INR 10,000."])
    evaluator = _FakeEvaluator(
        [ResponseEvaluation(True, False, "All claims are supported.")]
    )

    node = module.make_response_generator_node(
        settings, gateway, _FakeGuardrails(), evaluator
    )
    result = await node(_state())

    assert result["response_text"] == "The policy allows INR 10,000."
    assert result["evaluation_status"] == "passed"
    assert result["evaluation_attempts"] == 1
    assert result["human_review_required"] is False
    assert len(gateway.requests) == 1
    assert fake_stream_writer == [{"delta": "The policy allows INR 10,000."}]


@pytest.mark.asyncio
async def test_hallucinated_first_answer_is_corrected_before_emission(
    settings, fake_stream_writer
):
    gateway = _FakeGateway(
        [
            "The policy allows INR 50,000.",
            "The policy allows INR 10,000.",
        ]
    )
    evaluator = _FakeEvaluator(
        [
            ResponseEvaluation(False, True, "INR 50,000 is not supported by the policy."),
            ResponseEvaluation(True, False, "The corrected amount is supported."),
        ]
    )

    node = module.make_response_generator_node(
        settings, gateway, _FakeGuardrails(), evaluator
    )
    result = await node(_state())

    assert result["response_text"] == "The policy allows INR 10,000."
    assert result["evaluation_status"] == "corrected"
    assert result["evaluation_attempts"] == 2
    assert result["human_review_required"] is False
    assert len(gateway.requests) == 2
    assert "INR 50,000 is not supported" in gateway.requests[1].messages[0].content
    assert fake_stream_writer == [{"delta": "The policy allows INR 10,000."}]


@pytest.mark.asyncio
async def test_second_failed_evaluation_requires_human_review(
    settings, fake_stream_writer
):
    gateway = _FakeGateway(
        [
            "The policy allows INR 50,000.",
            "The policy allows INR 25,000.",
        ]
    )
    evaluator = _FakeEvaluator(
        [
            ResponseEvaluation(False, True, "INR 50,000 is unsupported."),
            ResponseEvaluation(False, True, "INR 25,000 is also unsupported."),
        ]
    )

    node = module.make_response_generator_node(
        settings, gateway, _FakeGuardrails(), evaluator
    )
    result = await node(_state())

    assert result["evaluation_status"] == "human_review_required"
    assert result["evaluation_attempts"] == 2
    assert result["human_review_required"] is True
    assert result["response_text"].startswith("I couldn't provide a sufficiently verified")
    assert fake_stream_writer == [{"delta": result["response_text"]}]
