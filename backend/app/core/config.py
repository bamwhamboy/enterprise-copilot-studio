"""Application configuration.

All runtime configuration is centralized here as a single, strongly-typed
``Settings`` object, populated from environment variables (and an optional
``.env`` file). Nothing outside this module should read ``os.environ``
directly — this keeps configuration auditable and easy to override in
tests, Docker, and CI.

Settings are grouped by concern:

* Application  — service identity, environment, debug flags
* API          — host/port/prefix/CORS
* Database     — PostgreSQL connection (used now, via SQLAlchemy)
* Future AI services — Redis, Qdrant, and LLM gateway connection details.
  These fields exist so the app is *configured* for upcoming phases, but
  no code in this phase actually connects to or calls these services.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["local", "development", "staging", "production"]


class Settings(BaseSettings):
    """Centralized, environment-driven application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- Application -----------------------------------------------------
    APP_NAME: str = "Enterprise Copilot Studio API"
    APP_ENV: Environment = "local"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # --- API ---------------------------------------------------------------
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    API_V1_PREFIX: str = "/api/v1"
    # Comma-separated list of allowed origins, e.g. "http://localhost:3000,https://app.example.com".
    # Stored as a plain string (not list[str]) because pydantic-settings expects
    # list-typed env values to be JSON, which is awkward to hand-author in a .env file.
    CORS_ORIGINS: str = "http://localhost:3000"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origins_list(self) -> list[str]:
        """Parsed, whitespace-trimmed list form of ``CORS_ORIGINS``."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    # --- Database (PostgreSQL via SQLAlchemy) -------------------------------
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ecs"
    DATABASE_POOL_SIZE: int = 5
    DATABASE_ECHO: bool = False

    # --- Future AI services (configured, not yet used in code) -------------
    # Populated so the platform is ready to wire these in a later phase.
    REDIS_URL: str | None = "redis://localhost:6379/0"
    QDRANT_URL: str | None = "http://localhost:6333"
    QDRANT_API_KEY: str | None = None
    LLM_GATEWAY_BASE_URL: str | None = None
    GROQ_API_KEY: str | None = None
    OPENAI_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None
    AZURE_OPENAI_API_KEY: str | None = None
    AZURE_OPENAI_ENDPOINT: str | None = None
    AZURE_OPENAI_API_VERSION: str = "2024-10-21"
    OLLAMA_BASE_URL: str | None = "http://localhost:11434"

    # --- Knowledge ingestion (Sprint 3A) -------------------------------------
    # Base directory (relative to the process working directory, or absolute)
    # where uploaded documents and their extracted text are stored.
    STORAGE_DIR: str = "storage/documents"
    MAX_UPLOAD_SIZE_MB: int = 25

    # --- LLM defaults (Sprint 4 — AI infrastructure, no calls made) ---------
    # These are the defaults the LLM Gateway (app/llm/gateway.py) and
    # Prompt Engine (app/prompt_engine/) fall back to when a caller doesn't
    # specify an override. Nothing in this codebase calls a model with them
    # yet — Sprint 4 builds only the routing/config layer.
    DEFAULT_LLM_PROVIDER: Literal["groq", "openai", "azure_openai", "anthropic"] = "groq"
    DEFAULT_LLM_MODEL: str = "groq-llama-3"
    DEFAULT_TEMPERATURE: float = 0.2
    DEFAULT_MAX_TOKENS: int = 1024

    # --- Enterprise Hybrid Hierarchical RAG (Sprint 3B) -----------------------
    QDRANT_COLLECTION_NAME: str = "knowledge_chunks"
    EMBEDDING_MODEL_NAME: str = "BAAI/bge-small-en-v1.5"
    EMBEDDING_DIMENSION: int = 384
    # Hierarchical chunking sizes, largest (document/section) to smallest
    # (paragraph), in tokens — passed straight to LlamaIndex's
    # HierarchicalNodeParser.
    CHUNK_SIZES: list[int] = Field(default_factory=lambda: [2048, 512, 128])
    HYBRID_SEMANTIC_TOP_K: int = 10
    HYBRID_BM25_TOP_K: int = 10
    HYBRID_FINAL_TOP_K: int = 5
    CONTEXT_COMPRESSION_MAX_CHUNKS: int = 5
    CONTEXT_COMPRESSION_MAX_CHARS_PER_CHUNK: int = 1200

    # --- Enterprise AI Runtime (Sprint 5) ------------------------------------
    MAX_CONVERSATION_HISTORY_MESSAGES: int = 20
    GUARDRAILS_INPUT_ENABLED: bool = True
    GUARDRAILS_OUTPUT_ENABLED: bool = True
    GUARDRAILS_PII_MASKING_ENABLED: bool = True
    RAG_QUERY_REWRITE_ENABLED: bool = True
    RAG_RERANK_ENABLED: bool = True


@lru_cache
def get_settings() -> Settings:
    """Return a cached ``Settings`` instance.

    ``lru_cache`` ensures environment variables are read once per process,
    while still allowing dependency-injected overrides in tests via
    ``app.dependency_overrides``.
    """
    return Settings()
