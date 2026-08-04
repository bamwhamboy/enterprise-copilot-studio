"""Tests for /api/v1/documents."""

import pytest
from httpx import AsyncClient

KS_BASE = "/api/v1/knowledge-sources"
DOC_BASE = "/api/v1/documents"


async def _create_knowledge_source(client: AsyncClient, name: str = "Doc Test Source") -> str:
    response = await client.post(KS_BASE, json={"name": name})
    return response.json()["id"]


@pytest.mark.asyncio
async def test_create_document(client: AsyncClient) -> None:
    ks_id = await _create_knowledge_source(client, "Source For Create")
    response = await client.post(
        DOC_BASE,
        json={
            "knowledge_source_id": ks_id,
            "name": "Leave Policy.pdf",
            "status": "indexed",
            "pages": 6,
            "chunks": 41,
            "embeddings": 41,
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Leave Policy.pdf"
    assert body["knowledge_source_id"] == ks_id


@pytest.mark.asyncio
async def test_create_document_missing_parent_returns_404(client: AsyncClient) -> None:
    response = await client.post(
        DOC_BASE,
        json={
            "knowledge_source_id": "00000000-0000-0000-0000-000000000000",
            "name": "Orphan.pdf",
        },
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_documents_filtered_by_knowledge_source(client: AsyncClient) -> None:
    ks_id = await _create_knowledge_source(client, "Filter Source")
    other_ks_id = await _create_knowledge_source(client, "Other Source")

    await client.post(DOC_BASE, json={"knowledge_source_id": ks_id, "name": "In Scope.pdf"})
    await client.post(DOC_BASE, json={"knowledge_source_id": other_ks_id, "name": "Out Of Scope.pdf"})

    response = await client.get(DOC_BASE, params={"knowledge_source_id": ks_id})
    assert response.status_code == 200
    names = [doc["name"] for doc in response.json()]
    assert names == ["In Scope.pdf"]


@pytest.mark.asyncio
async def test_get_document_not_found(client: AsyncClient) -> None:
    response = await client.get(f"{DOC_BASE}/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_document(client: AsyncClient) -> None:
    ks_id = await _create_knowledge_source(client, "Delete Doc Source")
    created = (
        await client.post(DOC_BASE, json={"knowledge_source_id": ks_id, "name": "Bye.pdf"})
    ).json()

    delete_response = await client.delete(f"{DOC_BASE}/{created['id']}")
    assert delete_response.status_code == 204

    get_response = await client.get(f"{DOC_BASE}/{created['id']}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_deleting_knowledge_source_cascades_to_documents(client: AsyncClient) -> None:
    ks_id = await _create_knowledge_source(client, "Cascade Source")
    created = (
        await client.post(DOC_BASE, json={"knowledge_source_id": ks_id, "name": "Cascaded.pdf"})
    ).json()

    await client.delete(f"{KS_BASE}/{ks_id}")

    response = await client.get(f"{DOC_BASE}/{created['id']}")
    assert response.status_code == 404
