"""LLM provider abstraction.

Defines the shared LiteLLM-backed client implementation plus one
concrete client per supported provider (OpenAI, Groq, Azure OpenAI,
Anthropic, Ollama).

Sprint 4 defined this interface with `generate`/`stream` stubs that
deliberately raised NotImplementedError. Sprint 5 completes it: every
client now makes a real call via LiteLLM (github.com/BerriAI/litellm),
which gives a single, uniform acompletion()/acompletion(stream=True)
call surface across all five providers. Provider selection is entirely
configuration-driven -- to_litellm_model() below is the only place that
knows each provider's LiteLLM model-string prefix; no other code
branches on provider identity.

health() is unchanged from Sprint 4 -- still config-only, no network call.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass

import litellm

from app.core.config import Settings
from app.core.logging import get_logger
from app.llm.models import (
    GenerationRequest,
    GenerationResponse,
    LLMMessage,
    LLMProvider,
    ProviderHealth,
    StreamChunk,
    TokenUsage,
)

logger = get_logger(__name__)

_LITELLM_PREFIXES: dict[LLMProvider, str] = {
    LLMProvider.OPENAI: "",
    LLMProvider.GROQ: "groq/",
    LLMProvider.AZURE_OPENAI: "azure/",
    LLMProvider.ANTHROPIC: "anthropic/",
    LLMProvider.OLLAMA: "ollama/",
}


@dataclass(frozen=True)
class ProviderConfig:
    """Static, per-provider configuration derived from Settings."""

    provider: LLMProvider
    api_key: str | None
    base_url: str | None
    default_model: str
    configured: bool


def to_litellm_model(provider: LLMProvider, model: str) -> str:
    """Build the LiteLLM model string for a provider/model pair.

    A model may itself contain a slash, for example Groq's
    ``openai/gpt-oss-120b`` model identifier. That slash does not mean the
    provider prefix is already present. We therefore only skip prefixing
    when the model already starts with the expected provider prefix.
    """
    prefix = _LITELLM_PREFIXES[provider]
    if not prefix or model.startswith(prefix):
        return model
    return f"{prefix}{model}"


def _messages_to_dicts(messages: list[LLMMessage]) -> list[dict[str, str]]:
    return [
        {"role": "system" if m.role == "developer" else m.role, "content": m.content}
        for m in messages
    ]


class LiteLLMProviderClient:
    """Shared LiteLLM-backed implementation of generate()/stream()."""

    def __init__(self, config: ProviderConfig) -> None:
        self.config = config

    def health(self) -> ProviderHealth:
        message = (
            f"{self.config.provider.value} is configured."
            if self.config.configured
            else f"{self.config.provider.value} is missing required configuration."
        )
        return ProviderHealth(
            provider=self.config.provider,
            configured=self.config.configured,
            default_model=self.config.default_model,
            message=message,
        )

    def _call_kwargs(self, request: GenerationRequest) -> dict:
        model = to_litellm_model(self.config.provider, request.model or self.config.default_model)
        kwargs: dict = {
            "model": model,
            "messages": _messages_to_dicts(request.messages),
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        if self.config.api_key:
            kwargs["api_key"] = self.config.api_key
        if self.config.base_url:
            kwargs["api_base"] = self.config.base_url
        return kwargs

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        kwargs = self._call_kwargs(request)
        logger.info(
            "LiteLLM generate() [request_id=%s model=%s]", request.request_id, kwargs["model"]
        )
        response = await litellm.acompletion(**kwargs)
        choice = response.choices[0]
        content = choice.message.content or ""
        usage = getattr(response, "usage", None)
        return GenerationResponse(
            content=content,
            provider=self.config.provider,
            model=request.model or self.config.default_model,
            usage=TokenUsage(
                prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
                completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
                total_tokens=getattr(usage, "total_tokens", 0) or 0,
            ),
        )

    async def stream(self, request: GenerationRequest) -> AsyncIterator[StreamChunk]:
        kwargs = self._call_kwargs(request)
        kwargs["stream"] = True
        logger.info(
            "LiteLLM stream() [request_id=%s model=%s]", request.request_id, kwargs["model"]
        )
        model = request.model or self.config.default_model
        response_stream = await litellm.acompletion(**kwargs)
        async for chunk in response_stream:
            delta = chunk.choices[0].delta
            text = getattr(delta, "content", None) or ""
            finish_reason = chunk.choices[0].finish_reason
            yield StreamChunk(
                delta=text,
                provider=self.config.provider,
                model=model,
                is_final=finish_reason is not None,
            )


class OpenAIProviderClient(LiteLLMProviderClient):
    """OpenAI provider client, via LiteLLM."""


class GroqProviderClient(LiteLLMProviderClient):
    """Groq provider client, via LiteLLM."""


class AzureOpenAIProviderClient(LiteLLMProviderClient):
    """Azure OpenAI provider client, via LiteLLM."""


class AnthropicProviderClient(LiteLLMProviderClient):
    """Anthropic provider client, via LiteLLM."""


class OllamaProviderClient(LiteLLMProviderClient):
    """Ollama (local/self-hosted) provider client, via LiteLLM."""


BaseLLMProviderClient = LiteLLMProviderClient


_CLIENT_CLASSES: dict[LLMProvider, type[LiteLLMProviderClient]] = {
    LLMProvider.OPENAI: OpenAIProviderClient,
    LLMProvider.GROQ: GroqProviderClient,
    LLMProvider.AZURE_OPENAI: AzureOpenAIProviderClient,
    LLMProvider.ANTHROPIC: AnthropicProviderClient,
    LLMProvider.OLLAMA: OllamaProviderClient,
}


def build_provider_configs(settings: Settings) -> dict[LLMProvider, ProviderConfig]:
    return {
        LLMProvider.OPENAI: ProviderConfig(
            provider=LLMProvider.OPENAI,
            api_key=settings.OPENAI_API_KEY,
            base_url=None,
            default_model="gpt-4o",
            configured=bool(settings.OPENAI_API_KEY),
        ),
        LLMProvider.GROQ: ProviderConfig(
            provider=LLMProvider.GROQ,
            api_key=settings.GROQ_API_KEY,
            base_url=settings.LLM_GATEWAY_BASE_URL,
            default_model=settings.DEFAULT_LLM_MODEL,
            configured=bool(settings.GROQ_API_KEY),
        ),
        LLMProvider.AZURE_OPENAI: ProviderConfig(
            provider=LLMProvider.AZURE_OPENAI,
            api_key=settings.AZURE_OPENAI_API_KEY,
            base_url=settings.AZURE_OPENAI_ENDPOINT,
            default_model="gpt-4o",
            configured=bool(
                settings.AZURE_OPENAI_API_KEY and settings.AZURE_OPENAI_ENDPOINT
            ),
        ),
        LLMProvider.ANTHROPIC: ProviderConfig(
            provider=LLMProvider.ANTHROPIC,
            api_key=settings.ANTHROPIC_API_KEY,
            base_url=None,
            default_model="claude-3-5-sonnet-latest",
            configured=bool(settings.ANTHROPIC_API_KEY),
        ),
        LLMProvider.OLLAMA: ProviderConfig(
            provider=LLMProvider.OLLAMA,
            api_key=None,
            base_url=settings.OLLAMA_BASE_URL,
            default_model="llama3",
            configured=bool(settings.OLLAMA_BASE_URL),
        ),
    }


def build_provider_clients(settings: Settings) -> dict[LLMProvider, LiteLLMProviderClient]:
    configs = build_provider_configs(settings)
    return {provider: _CLIENT_CLASSES[provider](config) for provider, config in configs.items()}
