"""Integration tests for the request context / correlation ID middleware."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_response_has_request_id_and_correlation_id_headers(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert "x-request-id" in response.headers
    assert "x-correlation-id" in response.headers


@pytest.mark.asyncio
async def test_correlation_id_is_echoed_back_when_supplied(client: AsyncClient) -> None:
    response = await client.get("/health", headers={"X-Correlation-ID": "fixed-corr-id"})
    assert response.headers["x-correlation-id"] == "fixed-corr-id"


@pytest.mark.asyncio
async def test_correlation_id_is_generated_when_absent(client: AsyncClient) -> None:
    response = await client.get("/health")
    correlation_id = response.headers["x-correlation-id"]
    assert correlation_id  # non-empty
    assert len(correlation_id) == 36  # UUID4 string length


@pytest.mark.asyncio
async def test_each_request_gets_a_distinct_request_id(client: AsyncClient) -> None:
    first = await client.get("/health")
    second = await client.get("/health")
    assert first.headers["x-request-id"] != second.headers["x-request-id"]
