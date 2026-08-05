"""LLM data models.

Strongly-typed request/response contracts shared by the gateway and every
provider client. These describe *shapes*, not behavior — no network I/O
lives here.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class LLMProvider(str, Enum):
    """Providers the gateway knows how to route to.

    Adding a provider here is a configuration change; it does not, by
    itself, add API-calling capability — that happens when a concrete
    client's ``generate``/``stream`` methods are implemented (Sprint 5,
    via LiteLLM — see ``providers.py``).
    """

    OPENAI = "openai"
    GROQ = "groq"
    AZURE_OPENAI = "azure_openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"


MessageRole = Literal["system", "developer", "user", "assistant"]


class LLMMessage(BaseModel):
    """A single message in a conversation, provider-agnostic."""

    role: MessageRole
    content: str


class GenerationRequest(BaseModel):
    """A request to generate a completion.

    ``provider`` and ``model`` are optional overrides; when omitted the
    gateway falls back to ``Settings.DEFAULT_LLM_PROVIDER`` /
    ``Settings.DEFAULT_LLM_MODEL``.
    """

    messages: list[LLMMessage]
    provider: LLMProvider | None = None
    model: str | None = None
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, gt=0)
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class TokenUsage(BaseModel):
    """Placeholder usage accounting shape — populated once real calls exist."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class GenerationResponse(BaseModel):
    """The result of a (future) completion call."""

    content: str
    provider: LLMProvider
    model: str
    usage: TokenUsage = Field(default_factory=TokenUsage)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StreamChunk(BaseModel):
    """A single chunk of a (future) streamed completion."""

    delta: str
    provider: LLMProvider
    model: str
    is_final: bool = False


class ProviderHealth(BaseModel):
    """Configuration-derived readiness for a single provider.

    This reflects whether a provider is *configured* (has the settings
    it needs), not whether its API is currently reachable — Sprint 4
    makes no network calls, including for health checks.
    """

    provider: LLMProvider
    configured: bool
    default_model: str | None = None
    message: str
