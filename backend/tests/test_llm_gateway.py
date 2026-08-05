"""Tests for app.llm — provider config, gateway routing, and the
NotImplementedError boundary. No network calls anywhere.
"""

import pytest

from app.core.config import get_settings
from app.llm.gateway import LLMGateway, ProviderNotConfiguredError
from app.llm.models import GenerationRequest, LLMMessage, LLMProvider
from app.llm.providers import build_provider_clients, build_provider_configs


def test_build_provider_configs_covers_all_four_providers() -> None:
    configs = build_provider_configs(get_settings())
    assert set(configs.keys()) == {
        LLMProvider.OPENAI,
        LLMProvider.GROQ,
        LLMProvider.AZURE_OPENAI,
        LLMProvider.ANTHROPIC,
    }


@pytest.mark.asyncio
async def test_gateway_routes_to_default_provider_when_unspecified() -> None:
    settings = get_settings()
    clients = build_provider_clients(settings)
    gateway = LLMGateway(settings, clients)

    request = GenerationRequest(messages=[LLMMessage(role="user", content="hi")])

    with pytest.raises(NotImplementedError) as exc_info:
        await gateway.generate(request)

    assert settings.DEFAULT_LLM_PROVIDER in str(exc_info.value)


@pytest.mark.asyncio
async def test_gateway_routes_to_explicit_provider_override() -> None:
    settings = get_settings()
    clients = build_provider_clients(settings)
    gateway = LLMGateway(settings, clients)

    request = GenerationRequest(
        messages=[LLMMessage(role="user", content="hi")],
        provider=LLMProvider.ANTHROPIC,
    )

    with pytest.raises(NotImplementedError) as exc_info:
        await gateway.generate(request)

    assert "anthropic" in str(exc_info.value)


@pytest.mark.asyncio
async def test_gateway_raises_for_unregistered_provider() -> None:
    settings = get_settings()
    gateway = LLMGateway(settings, clients={})  # no providers registered

    request = GenerationRequest(messages=[LLMMessage(role="user", content="hi")])

    with pytest.raises(ProviderNotConfiguredError):
        await gateway.generate(request)


@pytest.mark.asyncio
async def test_gateway_health_reports_all_providers_without_network_calls() -> None:
    settings = get_settings()
    clients = build_provider_clients(settings)
    gateway = LLMGateway(settings, clients)

    results = await gateway.health()

    assert len(results) == 4
    assert {r.provider for r in results} == {
        LLMProvider.OPENAI,
        LLMProvider.GROQ,
        LLMProvider.AZURE_OPENAI,
        LLMProvider.ANTHROPIC,
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
async def test_gateway_stream_also_raises_not_implemented() -> None:
    settings = get_settings()
    clients = build_provider_clients(settings)
    gateway = LLMGateway(settings, clients)

    request = GenerationRequest(messages=[LLMMessage(role="user", content="hi")])

    with pytest.raises(NotImplementedError):
        async for _ in gateway.stream(request):
            pass
