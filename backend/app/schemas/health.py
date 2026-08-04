"""Schemas for the health/liveness endpoint."""

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Response body for ``GET /health``."""

    status: str = Field(default="ok", description="Overall service status.")
    app_name: str = Field(description="Human-readable service name.")
    version: str = Field(description="Deployed application version.")
    environment: str = Field(description="Current runtime environment.")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC time the response was generated.",
    )
