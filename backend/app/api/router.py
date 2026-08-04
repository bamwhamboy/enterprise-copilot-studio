"""Top-level API router.

Aggregates all sub-routers so ``main.py`` only ever imports one object.
``/health`` is mounted unversioned (standard for liveness/readiness
probes behind load balancers); future business endpoints will be added
under ``settings.API_V1_PREFIX`` as this router grows.
"""

from fastapi import APIRouter

from app.api.v1 import health

api_router = APIRouter()
api_router.include_router(health.router)
