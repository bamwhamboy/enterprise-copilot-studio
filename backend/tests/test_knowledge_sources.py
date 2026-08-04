"""Tests for /api/v1/knowledge-sources."""

import pytest
from httpx import AsyncClient

BASE = "/api/v1/knowledge-sources"


@pytest.mark.asyncio
async def test_create_knowledge_source(client: AsyncClient) -> None:
    response = await client.post(
        BASE, json={"name": "Finance Docs", "source_type": "documents", "status": "active"}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Finance Docs"
    assert body["documents"] == []


@pytest.mark.asyncio
async def test_create_knowledge_source_defaults(client: AsyncClient) -> None:
    response = await client.post(BASE, json={"name": "Defaults Source"})
    assert response.status_code == 201
    body = response.json()
    assert body["source_type"] == "documents"
    assert body["status"] == "active"


@pytest.mark.asyncio
async def test_list_knowledge_sources(client: AsyncClient) -> None:
    await client.post(BASE, json={"name": "Listed Source"})
    response = await client.get(BASE)
    assert response.status_code == 200
    names = [ks["name"] for ks in response.json()]
    assert "Listed Source" in names


@pytest.mark.asyncio
async def test_get_knowledge_source(client: AsyncClient) -> None:
    created = (await client.post(BASE, json={"name": "Gettable Source"})).json()
    response = await client.get(f"{BASE}/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


@pytest.mark.asyncio
async def test_get_knowledge_source_not_found(client: AsyncClient) -> None:
    response = await client.get(f"{BASE}/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_knowledge_source(client: AsyncClient) -> None:
    created = (await client.post(BASE, json={"name": "Old Name"})).json()
    response = await client.put(f"{BASE}/{created['id']}", json={"name": "New Name"})
    assert response.status_code == 200
    assert response.json()["name"] == "New Name"


@pytest.mark.asyncio
async def test_delete_knowledge_source(client: AsyncClient) -> None:
    created = (await client.post(BASE, json={"name": "Deletable Source"})).json()
    delete_response = await client.delete(f"{BASE}/{created['id']}")
    assert delete_response.status_code == 204

    get_response = await client.get(f"{BASE}/{created['id']}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_create_knowledge_source_invalid_type(client: AsyncClient) -> None:
    response = await client.post(BASE, json={"name": "Bad Type", "source_type": "carrier-pigeon"})
    assert response.status_code == 422
