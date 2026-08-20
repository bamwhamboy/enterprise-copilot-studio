"""Top-level API router.

Aggregates all sub-routers so ``main.py`` only ever imports one object.
``/health`` is mounted unversioned (standard for liveness/readiness
probes behind load balancers). Business endpoints are mounted under
``settings.API_V1_PREFIX`` (``/api/v1``).
"""

from fastapi import APIRouter

from app.api.v1 import (
    auth,
    chat,
    chunks,
    copilots,
    documents,
    document_intelligence,
    health,
    index,
    knowledge_sources,
    organizations,
    roles,
    search,
    users,
)
from app.core.config import get_settings

settings = get_settings()

api_router = APIRouter()
api_router.include_router(health.router)

v1_router = APIRouter(prefix=settings.API_V1_PREFIX)
v1_router.include_router(auth.router)
v1_router.include_router(users.router)
v1_router.include_router(organizations.router)
v1_router.include_router(roles.router)
v1_router.include_router(copilots.router)
v1_router.include_router(knowledge_sources.router)
v1_router.include_router(documents.router)
v1_router.include_router(document_intelligence.router)
v1_router.include_router(index.router)
v1_router.include_router(search.router)
v1_router.include_router(chunks.router)
v1_router.include_router(chat.router)

api_router.include_router(v1_router)
