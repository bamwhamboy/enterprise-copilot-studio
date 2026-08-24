"""Application configuration.

All runtime configuration is centralized here as a single, strongly-typed
``Settings`` object, populated from environment variables (and an optional
``.env`` file). Nothing outside this module should read ``os.environ``
directly — this keeps configuration auditable and easy to override in
tests, Docker, and CI.
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

    # --- AI services --------------------------------------------------------
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
    STORAGE_DIR: str = "storage/documents"
    MAX_UPLOAD_SIZE_MB: int = 25

    # --- LLM defaults (Sprint 4/5) ------------------------------------------
    DEFAULT_LLM_PROVIDER: Literal["groq", "openai", "azure_openai", "anthropic"] = "groq"
    DEFAULT_LLM_MODEL: str = "openai/gpt-oss-120b"
    DEFAULT_TEMPERATURE: float = 0.2
    DEFAULT_MAX_TOKENS: int = 1024

    # --- Online response evaluation / hallucination guardrail ----------------
    # W&B Weave traces the judge and stores evaluation results. The evaluator
    # model is deliberately configurable because judge quality/cost should be
    # independently tunable from the generation model.
    WANDB_API_KEY: str | None = None
    WEAVE_PROJECT: str = "enterprise-copilot-studio"
    RESPONSE_EVALUATION_ENABLED: bool = True
    RESPONSE_EVALUATOR_MODEL: str = "groq/openai/gpt-oss-20b"
    RESPONSE_MAX_EVALUATION_ATTEMPTS: int = 2

    # --- Enterprise Hybrid Hierarchical RAG (Sprint 3B) -----------------------
    QDRANT_COLLECTION_NAME: str = "knowledge_chunks"
    EMBEDDING_MODEL_NAME: str = "BAAI/bge-small-en-v1.5"
    EMBEDDING_DIMENSION: int = 384
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

    # --- Authentication & Authorization (Sprint 6) ---------------------------
    JWT_SECRET_KEY: str = "dev-only-insecure-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14


@lru_cache
def get_settings() -> Settings:
    """Return a cached ``Settings`` instance."""
    return Settings()
