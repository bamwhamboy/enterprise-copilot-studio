"""Static model registry -- the single source of truth for known LLM models.

The registry maps model IDs to their providers and default status. It is used
for Copilot model validation and runtime provider resolution.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.llm.models import LLMProvider


@dataclass(frozen=True)
class ModelInfo:
    """One known model."""

    model_id: str
    provider: LLMProvider
    display_name: str
    is_default: bool = False


MODEL_REGISTRY: list[ModelInfo] = [
    # Groq
    ModelInfo(
        model_id="openai/gpt-oss-120b",
        provider=LLMProvider.GROQ,
        display_name="GPT-OSS 120B (Groq)",
        is_default=True,
    ),
    ModelInfo(
        model_id="groq/openai/gpt-oss-20b",
        provider=LLMProvider.GROQ,
        display_name="GPT-OSS 20B (Groq, response evaluator)",
    ),
    # OpenAI
    ModelInfo(
        model_id="gpt-4o",
        provider=LLMProvider.OPENAI,
        display_name="GPT-4o",
        is_default=True,
    ),
    # Azure OpenAI
    ModelInfo(
        model_id="gpt-4o",
        provider=LLMProvider.AZURE_OPENAI,
        display_name="GPT-4o (Azure OpenAI)",
        is_default=True,
    ),
    # Anthropic
    ModelInfo(
        model_id="claude-3-5-sonnet-latest",
        provider=LLMProvider.ANTHROPIC,
        display_name="Claude 3.5 Sonnet",
        is_default=True,
    ),
    # Ollama
    ModelInfo(
        model_id="llama3",
        provider=LLMProvider.OLLAMA,
        display_name="Llama 3 (Ollama)",
        is_default=True,
    ),
]


def list_models(provider: LLMProvider | None = None) -> list[ModelInfo]:
    """Return all registered models, optionally filtered by provider."""
    if provider is None:
        return list(MODEL_REGISTRY)
    return [entry for entry in MODEL_REGISTRY if entry.provider == provider]


def get_model(
    model_id: str,
    provider: LLMProvider | None = None,
) -> ModelInfo | None:
    """Look up a model by ID.

    ``groq/openai/gpt-oss-120b`` is accepted as an alias for the canonical
    registry entry ``openai/gpt-oss-120b``.
    """
    for entry in MODEL_REGISTRY:
        if entry.model_id == model_id and (
            provider is None or entry.provider == provider
        ):
            return entry

    if model_id == "groq/openai/gpt-oss-120b":
        return get_model("openai/gpt-oss-120b", provider=provider)

    return None


def resolve_model(model_id: str) -> ModelInfo:
    """Resolve a model ID to exactly one registered model.

    Raises ValueError for unknown models or models registered for multiple
    providers, such as ``gpt-4o``.
    """
    model_info = get_model(model_id)

    if model_info is None:
        raise ValueError(f"Unknown LLM model: {model_id}")

    matches = [
        entry for entry in MODEL_REGISTRY
        if entry.model_id == model_info.model_id
    ]

    if len(matches) > 1:
        providers = ", ".join(entry.provider.value for entry in matches)
        raise ValueError(
            f"Model '{model_id}' is registered for multiple providers: "
            f"{providers}. Provider selection is required."
        )

    return model_info


def get_default_model_id(provider: LLMProvider) -> str | None:
    """Return the default model ID for a provider, if one exists."""
    for entry in MODEL_REGISTRY:
        if entry.provider == provider and entry.is_default:
            return entry.model_id
    return None
