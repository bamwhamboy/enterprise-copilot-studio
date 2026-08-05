"""LLM Gateway.

The single entry point future sprints call to talk to an LLM, regardless
of provider. Sprint 4 implements real provider **selection** — resolving
a request to the correct configured provider and model — but makes no
network calls itself: ``generate``/``stream`` delegate to a provider
client whose own methods raise ``NotImplementedError`` (see
``providers.py`` for why). ``health()`` is real, end to end.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from app.core.config import Settings
from app.core.logging import get_logger
from app.llm.models import (
    GenerationRequest,
    GenerationResponse,
    LLMProvider,
    ProviderHealth,
    StreamChunk,
)
from app.llm.providers import BaseLLMProviderClient

logger = get_logger(__name__)


class ProviderNotConfiguredError(Exception):
    """Raised when a request targets a provider with no registered client."""

    def __init__(self, provider: LLMProvider) -> None:
        super().__init__(f"No client registered for provider '{provider.value}'.")


class LLMGateway:
    """Routes generation requests to the appropriate configured provider.

    Built once per request via dependency injection — see
    ``app.core.dependencies.get_llm_gateway``.
    """

    def __init__(
        self, settings: Settings, clients: dict[LLMProvider, BaseLLMProviderClient]
    ) -> None:
        self._settings = settings
        self._clients = clients

    def _resolve_provider(self, request: GenerationRequest) -> LLMProvider:
        return request.provider or LLMProvider(self._settings.DEFAULT_LLM_PROVIDER)

    def _resolve_client(self, provider: LLMProvider) -> BaseLLMProviderClient:
        client = self._clients.get(provider)
        if client is None:
            raise ProviderNotConfiguredError(provider)
        return client

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        """Route to the selected provider and generate a completion.

        Routing (provider/model resolution + logging) is real. The
        actual network call is not implemented in Sprint 4 — the
        resolved provider client's ``generate()`` raises
        ``NotImplementedError``.
        """
        provider = self._resolve_provider(request)
        client = self._resolve_client(provider)
        model = request.model or client.config.default_model
        logger.info(
            "generate() routed [request_id=%s provider=%s model=%s]",
            request.request_id,
            provider.value,
            model,
        )
        return await client.generate(request)

    async def stream(self, request: GenerationRequest) -> AsyncIterator[StreamChunk]:
        """Route to the selected provider and stream a completion.

        Same routing/not-implemented split as ``generate()``.
        """
        provider = self._resolve_provider(request)
        client = self._resolve_client(provider)
        model = request.model or client.config.default_model
        logger.info(
            "stream() routed [request_id=%s provider=%s model=%s]",
            request.request_id,
            provider.value,
            model,
        )
        async for chunk in client.stream(request):
            yield chunk

    async def health(self, provider: LLMProvider | None = None) -> list[ProviderHealth]:
        """Report configuration readiness for one or all providers.

        Makes no network calls — reflects configuration only.
        """
        if provider is not None:
            return [self._resolve_client(provider).health()]
        return [client.health() for client in self._clients.values()]
