"""Tests for GET /health."""

import pytest
from httpx import AsyncClient

from app.core.config import get_settings


@pytest.mark.asyncio
async def test_health_returns_200(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_response_shape(client: AsyncClient) -> None:
    response = await client.get("/health")
    body = response.json()

    assert body["status"] == "ok"
    assert body["app_name"] == get_settings().APP_NAME
    assert body["version"] == get_settings().APP_VERSION
    assert body["environment"] == get_settings().APP_ENV
    assert "timestamp" in body


@pytest.mark.asyncio
async def test_health_sets_request_id_header(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert "x-request-id" in response.headers
