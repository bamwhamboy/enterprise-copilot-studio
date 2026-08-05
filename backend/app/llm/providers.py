"""LLM provider abstraction.

Defines ``BaseLLMProviderClient`` — the interface every provider client
implements (``generate``, ``stream``, ``health``) — plus one stub client
per supported provider (OpenAI, Groq, Azure OpenAI, Anthropic).

Per Sprint 4's scope: ``generate``/``stream`` deliberately raise
``NotImplementedError``. No network call is made anywhere in this
module. ``health()`` *is* real — it reports whether a provider has the
configuration it would need, without touching the network — because
that's a legitimate, callable capability that doesn't require an SDK
or an API call.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass

from app.core.config import Settings
from app.llm.models import (
    GenerationRequest,
    GenerationResponse,
    LLMProvider,
    ProviderHealth,
    StreamChunk,
)


@dataclass(frozen=True)
class ProviderConfig:
    """Static, per-provider configuration derived from ``Settings``."""

    provider: LLMProvider
    api_key: str | None
    base_url: str | None
    default_model: str
    configured: bool


class BaseLLMProviderClient(ABC):
    """The interface every provider client must implement.

    Sprint 4 defines this contract only — see module docstring for what
    is and isn't implemented.
    """

    def __init__(self, config: ProviderConfig) -> None:
        self.config = config

    @abstractmethod
    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        """Generate a single completion. Not implemented in Sprint 4."""
        raise NotImplementedError

    @abstractmethod
    def stream(self, request: GenerationRequest) -> AsyncIterator[StreamChunk]:
        """Stream a completion chunk by chunk. Not implemented in Sprint 4."""
        raise NotImplementedError

    def health(self) -> ProviderHealth:
        """Report configuration readiness. Makes no network calls."""
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


class _InterfaceOnlyProviderClient(BaseLLMProviderClient):
    """Shared stub body for generate/stream.

    Subclassed once per provider purely for clear naming/typing at call
    sites (``OpenAIProviderClient`` vs. ``GroqProviderClient``, etc.) —
    behavior is identical: raise, clearly, with no network I/O.
    """

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        raise NotImplementedError(
            f"{self.config.provider.value} generation is not implemented in Sprint 4 "
            "— this sprint defines the provider interface only."
        )

    async def stream(self, request: GenerationRequest) -> AsyncIterator[StreamChunk]:
        raise NotImplementedError(
            f"{self.config.provider.value} streaming is not implemented in Sprint 4 "
            "— this sprint defines the provider interface only."
        )
        yield  # pragma: no cover — keeps this a generator function; unreachable.


class OpenAIProviderClient(_InterfaceOnlyProviderClient):
    """OpenAI provider client. Interface only — see module docstring."""


class GroqProviderClient(_InterfaceOnlyProviderClient):
    """Groq provider client. Interface only — see module docstring."""


class AzureOpenAIProviderClient(_InterfaceOnlyProviderClient):
    """Azure OpenAI provider client. Interface only — see module docstring."""


class AnthropicProviderClient(_InterfaceOnlyProviderClient):
    """Anthropic provider client. Interface only — see module docstring."""


_CLIENT_CLASSES: dict[LLMProvider, type[BaseLLMProviderClient]] = {
    LLMProvider.OPENAI: OpenAIProviderClient,
    LLMProvider.GROQ: GroqProviderClient,
    LLMProvider.AZURE_OPENAI: AzureOpenAIProviderClient,
    LLMProvider.ANTHROPIC: AnthropicProviderClient,
}


def build_provider_configs(settings: Settings) -> dict[LLMProvider, ProviderConfig]:
    """Derive one ``ProviderConfig`` per supported provider from ``Settings``."""
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
    }


def build_provider_clients(settings: Settings) -> dict[LLMProvider, BaseLLMProviderClient]:
    """Build one client instance per provider, wired to its derived config."""
    configs = build_provider_configs(settings)
    return {provider: _CLIENT_CLASSES[provider](config) for provider, config in configs.items()}
