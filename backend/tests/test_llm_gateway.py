"""Tests for app.llm -- provider config, gateway routing, and the
completed (Sprint 5) LiteLLM-backed generate()/stream() calls.

No real network calls to a provider are made: litellm.acompletion is
monkeypatched with a fake response, which lets us verify the full
routing + request-shaping + response-shaping pipeline for real, without
needing actual API keys. Ollama connectivity (no key required) is
separately smoke-tested against the real network layer.
"""

from types import SimpleNamespace

import pytest

from app.core.config import get_settings
from app.llm.gateway import LLMGateway, ProviderNotConfiguredError
from app.llm.models import GenerationRequest, LLMMessage, LLMProvider
from app.llm.providers import build_provider_clients, build_provider_configs, to_litellm_model


def test_build_provider_configs_covers_all_five_providers() -> None:
    configs = build_provider_configs(get_settings())
    assert set(configs.keys()) == {
        LLMProvider.OPENAI,
        LLMProvider.GROQ,
        LLMProvider.AZURE_OPENAI,
        LLMProvider.ANTHROPIC,
        LLMProvider.OLLAMA,
    }


@pytest.mark.parametrize(
    "provider,model,expected",
    [
        (LLMProvider.OPENAI, "gpt-4o", "gpt-4o"),
        (LLMProvider.GROQ, "llama-3.1-70b-versatile", "groq/llama-3.1-70b-versatile"),
        (LLMProvider.ANTHROPIC, "claude-3-5-sonnet-latest", "anthropic/claude-3-5-sonnet-latest"),
        (LLMProvider.AZURE_OPENAI, "my-deployment", "azure/my-deployment"),
        (LLMProvider.OLLAMA, "llama3", "ollama/llama3"),
    ],
)
def test_to_litellm_model_prefixes_correctly(provider, model, expected) -> None:
    assert to_litellm_model(provider, model) == expected


def test_to_litellm_model_is_idempotent() -> None:
    # Already-prefixed model strings pass through unchanged.
    assert to_litellm_model(LLMProvider.GROQ, "groq/llama3") == "groq/llama3"


def _fake_completion_response(content: str = "Hello from the model!"):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(prompt_tokens=12, completion_tokens=4, total_tokens=16),
    )


@pytest.mark.asyncio
async def test_gateway_generate_routes_to_default_provider(monkeypatch) -> None:
    settings = get_settings()
    clients = build_provider_clients(settings)
    gateway = LLMGateway(settings, clients)

    captured = {}

    async def fake_acompletion(**kwargs):
        captured.update(kwargs)
        return _fake_completion_response("The leave policy allows 20 days.")

    monkeypatch.setattr("app.llm.providers.litellm.acompletion", fake_acompletion)

    request = GenerationRequest(messages=[LLMMessage(role="user", content="What's the leave policy?")])
    response = await gateway.generate(request)

    assert response.content == "The leave policy allows 20 days."
    assert response.provider.value == settings.DEFAULT_LLM_PROVIDER
    assert response.usage.total_tokens == 16
    assert captured["model"] == to_litellm_model(
        LLMProvider(settings.DEFAULT_LLM_PROVIDER), settings.DEFAULT_LLM_MODEL
    )
    assert captured["messages"] == [{"role": "user", "content": "What's the leave policy?"}]


@pytest.mark.asyncio
async def test_gateway_generate_routes_to_explicit_provider_override(monkeypatch) -> None:
    settings = get_settings()
    clients = build_provider_clients(settings)
    gateway = LLMGateway(settings, clients)

    captured = {}

    async def fake_acompletion(**kwargs):
        captured.update(kwargs)
        return _fake_completion_response()

    monkeypatch.setattr("app.llm.providers.litellm.acompletion", fake_acompletion)

    request = GenerationRequest(
        messages=[LLMMessage(role="user", content="hi")],
        provider=LLMProvider.ANTHROPIC,
        model="claude-3-5-sonnet-latest",
    )
    response = await gateway.generate(request)

    assert response.provider == LLMProvider.ANTHROPIC
    assert captured["model"] == "anthropic/claude-3-5-sonnet-latest"


@pytest.mark.asyncio
async def test_gateway_generate_maps_developer_role_to_system(monkeypatch) -> None:
    settings = get_settings()
    clients = build_provider_clients(settings)
    gateway = LLMGateway(settings, clients)

    captured = {}

    async def fake_acompletion(**kwargs):
        captured.update(kwargs)
        return _fake_completion_response()

    monkeypatch.setattr("app.llm.providers.litellm.acompletion", fake_acompletion)

    request = GenerationRequest(
        messages=[
            LLMMessage(role="system", content="You are helpful."),
            LLMMessage(role="developer", content="Respond concisely."),
            LLMMessage(role="user", content="hi"),
        ]
    )
    await gateway.generate(request)

    roles = [m["role"] for m in captured["messages"]]
    assert roles == ["system", "system", "user"]


@pytest.mark.asyncio
async def test_gateway_raises_for_unregistered_provider() -> None:
    settings = get_settings()
    gateway = LLMGateway(settings, clients={})  # no providers registered

    request = GenerationRequest(messages=[LLMMessage(role="user", content="hi")])

    with pytest.raises(ProviderNotConfiguredError):
        await gateway.generate(request)


@pytest.mark.asyncio
async def test_gateway_health_reports_all_five_providers_without_network_calls() -> None:
    settings = get_settings()
    clients = build_provider_clients(settings)
    gateway = LLMGateway(settings, clients)

    results = await gateway.health()

    assert len(results) == 5
    assert {r.provider for r in results} == {
        LLMProvider.OPENAI,
        LLMProvider.GROQ,
        LLMProvider.AZURE_OPENAI,
        LLMProvider.ANTHROPIC,
        LLMProvider.OLLAMA,
    }


@pytest.mark.asyncio
async def test_gateway_health_single_provider() -> None:
    settings = get_settings()
    clients = build_provider_clients(settings)
    gateway = LLMGateway(settings, clients)

    results = await gateway.health(LLMProvider.OPENAI)

    assert len(results) == 1
    assert results[0].provider == LLMProvider.OPENAI


@pytest.mark.asyncio
async def test_gateway_stream_yields_chunks(monkeypatch) -> None:
    settings = get_settings()
    clients = build_provider_clients(settings)
    gateway = LLMGateway(settings, clients)

    async def fake_stream():
        yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="Hel"), finish_reason=None)])
        yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="lo"), finish_reason=None)])
        yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=""), finish_reason="stop")])

    async def fake_acompletion(**kwargs):
        assert kwargs["stream"] is True
        return fake_stream()

    monkeypatch.setattr("app.llm.providers.litellm.acompletion", fake_acompletion)

    request = GenerationRequest(messages=[LLMMessage(role="user", content="hi")])
    chunks = [c async for c in gateway.stream(request)]

    assert [c.delta for c in chunks] == ["Hel", "lo", ""]
    assert chunks[-1].is_final is True
    assert chunks[0].is_final is False


@pytest.mark.asyncio
async def test_ollama_reaches_real_litellm_network_layer() -> None:
    """No API key needed for Ollama, so this hits litellm's actual HTTP
    layer (not monkeypatched) and confirms end-to-end wiring: it fails
    only because no Ollama server is running here, not due to a bug in
    our integration code.
    """
    settings = get_settings()
    clients = build_provider_clients(settings)
    gateway = LLMGateway(settings, clients)

    request = GenerationRequest(
        messages=[LLMMessage(role="user", content="hi")], provider=LLMProvider.OLLAMA
    )

    with pytest.raises(Exception) as exc_info:
        await gateway.generate(request)

    # A connection-layer failure, not an AttributeError/TypeError from our code.
    assert "connect" in str(exc_info.value).lower() or "connection" in str(exc_info.value).lower()
