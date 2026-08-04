"""Health check endpoint.

A pure liveness check: it reports that the process is up and reachable.
It intentionally does not depend on the database, Redis, or Qdrant, so it
stays meaningful even before those integrations are wired in — and so it
never fails the container's liveness probe due to a downstream outage.
"""

from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.health import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse, summary="Liveness check")
async def health_check() -> HealthResponse:
    """Return basic service metadata to confirm the API is running."""
    settings = get_settings()
    return HealthResponse(
        status="ok",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
    )
