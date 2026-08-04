"""Tests for /api/v1/copilots."""

import pytest
from httpx import AsyncClient

KS_BASE = "/api/v1/knowledge-sources"
COPILOT_BASE = "/api/v1/copilots"


async def _create_knowledge_source(client: AsyncClient, name: str = "Copilot Test Source") -> str:
    response = await client.post(KS_BASE, json={"name": name})
    return response.json()["id"]


@pytest.mark.asyncio
async def test_create_copilot_minimal(client: AsyncClient) -> None:
    response = await client.post(COPILOT_BASE, json={"name": "Minimal Copilot"})
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Minimal Copilot"
    assert body["domain"] == "hr"
    assert body["status"] == "draft"
    assert body["model"] == "groq-llama-3"
    assert body["knowledge_sources"] == []


@pytest.mark.asyncio
async def test_create_copilot_missing_name_returns_422(client: AsyncClient) -> None:
    response = await client.post(COPILOT_BASE, json={"domain": "hr"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_copilot_invalid_domain_returns_422(client: AsyncClient) -> None:
    response = await client.post(COPILOT_BASE, json={"name": "X", "domain": "marketing"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_copilot_with_knowledge_sources(client: AsyncClient) -> None:
    ks_id = await _create_knowledge_source(client, "Attached Source")
    response = await client.post(
        COPILOT_BASE,
        json={"name": "HR Copilot", "knowledge_source_ids": [ks_id]},
    )
    assert response.status_code == 201
    body = response.json()
    assert len(body["knowledge_sources"]) == 1
    assert body["knowledge_sources"][0]["id"] == ks_id


@pytest.mark.asyncio
async def test_list_copilots(client: AsyncClient) -> None:
    await client.post(COPILOT_BASE, json={"name": "Listed Copilot"})
    response = await client.get(COPILOT_BASE)
    assert response.status_code == 200
    names = [c["name"] for c in response.json()]
    assert "Listed Copilot" in names


@pytest.mark.asyncio
async def test_get_copilot_not_found(client: AsyncClient) -> None:
    response = await client.get(f"{COPILOT_BASE}/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_update_copilot_fields(client: AsyncClient) -> None:
    created = (await client.post(COPILOT_BASE, json={"name": "Draft Copilot"})).json()

    response = await client.put(
        f"{COPILOT_BASE}/{created['id']}",
        json={"status": "active", "model": "groq-llama-3-70b"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "active"
    assert body["model"] == "groq-llama-3-70b"
    assert body["name"] == "Draft Copilot"  # untouched fields preserved


@pytest.mark.asyncio
async def test_update_copilot_replaces_knowledge_sources(client: AsyncClient) -> None:
    ks_a = await _create_knowledge_source(client, "Source A")
    ks_b = await _create_knowledge_source(client, "Source B")

    created = (
        await client.post(
            COPILOT_BASE, json={"name": "Rewireable Copilot", "knowledge_source_ids": [ks_a]}
        )
    ).json()
    assert [ks["id"] for ks in created["knowledge_sources"]] == [ks_a]

    updated = (
        await client.put(
            f"{COPILOT_BASE}/{created['id']}", json={"knowledge_source_ids": [ks_b]}
        )
    ).json()
    assert [ks["id"] for ks in updated["knowledge_sources"]] == [ks_b]


@pytest.mark.asyncio
async def test_delete_copilot(client: AsyncClient) -> None:
    created = (await client.post(COPILOT_BASE, json={"name": "Deletable Copilot"})).json()

    delete_response = await client.delete(f"{COPILOT_BASE}/{created['id']}")
    assert delete_response.status_code == 204

    get_response = await client.get(f"{COPILOT_BASE}/{created['id']}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_deleting_copilot_does_not_delete_knowledge_source(client: AsyncClient) -> None:
    ks_id = await _create_knowledge_source(client, "Surviving Source")
    created = (
        await client.post(
            COPILOT_BASE, json={"name": "Ephemeral Copilot", "knowledge_source_ids": [ks_id]}
        )
    ).json()

    await client.delete(f"{COPILOT_BASE}/{created['id']}")

    response = await client.get(f"{KS_BASE}/{ks_id}")
    assert response.status_code == 200
