"""Tests for the Sprint 1 model registry foundation.

Covers: registry lookup, provider filtering, default-model metadata,
the DEFAULT_LLM_PROVIDER vocabulary now including "ollama", and --
critically -- that sourcing providers.py's default_model values from
the registry didn't change any of them (behavior-preserving refactor,
not a routing change).
"""

from typing import get_args

from app.core.config import Settings, get_settings
from app.llm.model_registry import MODEL_REGISTRY, get_default_model_id, get_model, list_models
from app.llm.models import LLMProvider
from app.llm.providers import build_provider_configs


# --- Registry lookup ---------------------------------------------------


def test_get_model_finds_a_known_model() -> None:
    entry = get_model("claude-3-5-sonnet-latest")
    assert entry is not None
    assert entry.provider == LLMProvider.ANTHROPIC
    assert entry.display_name == "Claude 3.5 Sonnet"


def test_get_model_returns_none_for_unknown_model_id() -> None:
    assert get_model("not-a-real-model") is None


def test_get_model_disambiguates_shared_model_id_by_provider() -> None:
    """"gpt-4o" is registered for both OpenAI and Azure OpenAI --
    passing provider disambiguates; omitting it returns the first
    match in declaration order (documented, not an error)."""
    openai_entry = get_model("gpt-4o", provider=LLMProvider.OPENAI)
    azure_entry = get_model("gpt-4o", provider=LLMProvider.AZURE_OPENAI)

    assert openai_entry is not None and openai_entry.provider == LLMProvider.OPENAI
    assert azure_entry is not None and azure_entry.provider == LLMProvider.AZURE_OPENAI
    assert openai_entry.display_name != azure_entry.display_name

    unscoped = get_model("gpt-4o")
    assert unscoped is not None
    assert unscoped == openai_entry  # first declared, per MODEL_REGISTRY order


def test_get_model_with_mismatched_provider_returns_none() -> None:
    assert get_model("claude-3-5-sonnet-latest", provider=LLMProvider.OPENAI) is None


# --- Provider filtering --------------------------------------------------


def test_list_models_with_no_filter_returns_everything() -> None:
    assert list_models() == MODEL_REGISTRY
    assert len(list_models()) == len(MODEL_REGISTRY)


def test_list_models_filters_by_provider() -> None:
    groq_models = list_models(provider=LLMProvider.GROQ)
    assert len(groq_models) == 2
    assert all(entry.provider == LLMProvider.GROQ for entry in groq_models)
    assert {entry.model_id for entry in groq_models} == {
        "openai/gpt-oss-120b",
        "groq/openai/gpt-oss-20b",
    }


def test_list_models_for_provider_with_one_entry() -> None:
    ollama_models = list_models(provider=LLMProvider.OLLAMA)
    assert len(ollama_models) == 1
    assert ollama_models[0].model_id == "llama3"


# --- Default model metadata ----------------------------------------------


def test_every_provider_has_exactly_one_default_model() -> None:
    for provider in LLMProvider:
        defaults = [entry for entry in list_models(provider) if entry.is_default]
        assert len(defaults) == 1, f"{provider} should have exactly one default model"


def test_get_default_model_id_matches_current_settings_defaults() -> None:
    # Groq's registry entry mirrors Settings.DEFAULT_LLM_MODEL's own
    # default value -- see model_registry.py's module docstring for
    # why providers.py doesn't actually read this one at runtime.
    assert get_default_model_id(LLMProvider.GROQ) == "openai/gpt-oss-120b"
    assert get_default_model_id(LLMProvider.OPENAI) == "gpt-4o"
    assert get_default_model_id(LLMProvider.AZURE_OPENAI) == "gpt-4o"
    assert get_default_model_id(LLMProvider.ANTHROPIC) == "claude-3-5-sonnet-latest"
    assert get_default_model_id(LLMProvider.OLLAMA) == "llama3"


def test_evaluator_model_is_registered_but_not_default() -> None:
    entry = get_model("groq/openai/gpt-oss-20b")
    assert entry is not None
    assert entry.provider == LLMProvider.GROQ
    assert entry.is_default is False


# --- Ollama provider configuration vocabulary (config.py) ---------------


def test_default_llm_provider_literal_includes_ollama() -> None:
    """Settings.DEFAULT_LLM_PROVIDER's allowed values must include
    "ollama" -- the provider layer already implements a full Ollama
    client; the settings vocabulary just hadn't caught up."""
    annotation = Settings.model_fields["DEFAULT_LLM_PROVIDER"].annotation
    assert "ollama" in get_args(annotation)


def test_settings_accepts_ollama_as_default_llm_provider() -> None:
    # Direct construction (not model_copy, which bypasses validation) --
    # this must actually pass through the Literal's validation, not
    # just be attribute-assignable.
    settings = Settings(DEFAULT_LLM_PROVIDER="ollama")
    assert settings.DEFAULT_LLM_PROVIDER == "ollama"


# --- Preservation of existing provider defaults --------------------------


def test_provider_defaults_are_unchanged_after_registry_sourcing() -> None:
    """The exact values providers.py returned before the registry
    existed must be identical now -- this is a source-of-truth
    refactor, not a behavior change."""
    configs = build_provider_configs(get_settings())

    assert configs[LLMProvider.OPENAI].default_model == "gpt-4o"
    assert configs[LLMProvider.GROQ].default_model == get_settings().DEFAULT_LLM_MODEL
    assert configs[LLMProvider.AZURE_OPENAI].default_model == "gpt-4o"
    assert configs[LLMProvider.ANTHROPIC].default_model == "claude-3-5-sonnet-latest"
    assert configs[LLMProvider.OLLAMA].default_model == "llama3"
