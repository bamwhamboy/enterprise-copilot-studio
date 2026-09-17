"""Static model registry -- the single source of truth for which
models this application currently knows about, and which provider
each belongs to.

This is Sprint 1's foundation only: a static, in-code catalog that
nothing else in the system consults yet. ``Copilot.model`` is not
validated against this (that's the later model-routing sprint's job),
and ``LLMGateway`` does not route through it -- it only routes on
``GenerationRequest.provider``/``model`` exactly as before. The one
thing that DOES read from here today is ``app/llm/providers.py``'s
per-provider ``default_model``, for the providers whose default was
already a hardcoded literal (OpenAI, Azure OpenAI, Anthropic, Ollama).
Groq's default stays wired to ``Settings.DEFAULT_LLM_MODEL`` exactly
as before -- it was never a hardcoded literal to begin with, so
pointing it at a static registry entry instead would be a real
behavior change (losing settings-driven configurability), not a
behavior-preserving refactor.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.llm.models import LLMProvider


@dataclass(frozen=True)
class ModelInfo:
    """One known model. ``is_default`` marks the model a provider's
    ``ProviderConfig.default_model`` resolves to when a request omits
    an explicit model -- see ``get_default_model_id`` below."""

    model_id: str
    provider: LLMProvider
    display_name: str
    is_default: bool = False


# Every entry here matches a value that already exists elsewhere in
# the codebase today (Settings.DEFAULT_LLM_MODEL,
# Settings.RESPONSE_EVALUATOR_MODEL, or a literal in
# build_provider_configs) -- this registry describes the current
# state, it doesn't introduce new models.
MODEL_REGISTRY: list[ModelInfo] = [
    # Groq -- matches Settings.DEFAULT_LLM_MODEL's default. Still the
    # single source of truth for Groq's *actual* default is Settings,
    # not this entry (see module docstring); this entry exists for
    # discoverability/listing, not for providers.py to read from.
    ModelInfo(
        model_id="openai/gpt-oss-120b",
        provider=LLMProvider.GROQ,
        display_name="GPT-OSS 120B (Groq)",
        is_default=True,
    ),
    # Matches Settings.RESPONSE_EVALUATOR_MODEL's default -- the
    # online response evaluator (app/evaluation/response_evaluator.py)
    # deliberately uses a smaller/cheaper model than generation.
    ModelInfo(
        model_id="groq/openai/gpt-oss-20b",
        provider=LLMProvider.GROQ,
        display_name="GPT-OSS 20B (Groq, response evaluator)",
    ),
    ModelInfo(
        model_id="gpt-4o",
        provider=LLMProvider.OPENAI,
        display_name="GPT-4o",
        is_default=True,
    ),
    # Same model_id as OpenAI's entry above (Azure OpenAI deployments
    # commonly name themselves after the underlying model) -- see
    # get_model()'s docstring for how that ambiguity is handled.
    ModelInfo(
        model_id="gpt-4o",
        provider=LLMProvider.AZURE_OPENAI,
        display_name="GPT-4o (Azure OpenAI)",
        is_default=True,
    ),
    ModelInfo(
        model_id="claude-3-5-sonnet-latest",
        provider=LLMProvider.ANTHROPIC,
        display_name="Claude 3.5 Sonnet",
        is_default=True,
    ),
    ModelInfo(
        model_id="llama3",
        provider=LLMProvider.OLLAMA,
        display_name="Llama 3 (Ollama)",
        is_default=True,
    ),
]


def list_models(provider: LLMProvider | None = None) -> list[ModelInfo]:
    """All registered models, optionally filtered to one provider.

    Returns entries in registry declaration order.
    """
    if provider is None:
        return list(MODEL_REGISTRY)
    return [entry for entry in MODEL_REGISTRY if entry.provider == provider]


def get_model(model_id: str, provider: LLMProvider | None = None) -> ModelInfo | None:
    """Look up one model by id.

    ``model_id`` alone is not always unique across providers (e.g.
    "gpt-4o" is registered for both OpenAI and Azure OpenAI, since
    Azure deployments are commonly named after the underlying model).
    Pass ``provider`` to disambiguate; without it, this returns the
    first match in registry declaration order. Resolving that
    ambiguity properly (e.g. from a copilot's actual configured
    provider) is model-routing work, out of scope for this registry.
    """
    for entry in MODEL_REGISTRY:
        if entry.model_id == model_id and (provider is None or entry.provider == provider):
            return entry
    return None


def get_default_model_id(provider: LLMProvider) -> str | None:
    """The model_id marked as default for a given provider, or None
    if no entry is marked default for it."""
    for entry in MODEL_REGISTRY:
        if entry.provider == provider and entry.is_default:
            return entry.model_id
    return None
