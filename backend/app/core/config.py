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

from pydantic import computed_field
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


@lru_cache
def get_settings() -> Settings:
    """Return a cached ``Settings`` instance.

    ``lru_cache`` ensures environment variables are read once per process,
    while still allowing dependency-injected overrides in tests via
    ``app.dependency_overrides``.
    """
    return Settings()
