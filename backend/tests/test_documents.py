"""Tests for /api/v1/documents."""

import pytest
from httpx import AsyncClient

KS_BASE = "/api/v1/knowledge-sources"
DOC_BASE = "/api/v1/documents"


def _auth_headers(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _create_knowledge_source(
    client: AsyncClient, headers: dict, name: str = "Doc Test Source"
) -> str:
    response = await client.post(KS_BASE, json={"name": name}, headers=headers)
    return response.json()["id"]


@pytest.mark.asyncio
async def test_create_document(client: AsyncClient, register_and_login) -> None:
    headers = _auth_headers(await register_and_login(email="doc1@example.com"))
    ks_id = await _create_knowledge_source(client, headers, "Source For Create")
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
        headers=headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Leave Policy.pdf"
    assert body["knowledge_source_id"] == ks_id


@pytest.mark.asyncio
async def test_create_document_requires_auth(client: AsyncClient) -> None:
    response = await client.post(
        DOC_BASE,
        json={
            "knowledge_source_id": "00000000-0000-0000-0000-000000000000",
            "name": "No Auth.pdf",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_document_missing_parent_returns_404(
    client: AsyncClient, register_and_login
) -> None:
    headers = _auth_headers(await register_and_login(email="doc2@example.com"))
    response = await client.post(
        DOC_BASE,
        json={
            "knowledge_source_id": "00000000-0000-0000-0000-000000000000",
            "name": "Orphan.pdf",
        },
        headers=headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_cannot_create_document_under_another_organizations_knowledge_source(
    client: AsyncClient, register_and_login
) -> None:
    """A user shouldn't be able to attach a document to a knowledge
    source that isn't theirs just by knowing its id.
    """
    org_a_headers = _auth_headers(
        await register_and_login(
            email="doc-org-a@example.com", organization_name="Doc Org A"
        )
    )
    ks_id = await _create_knowledge_source(client, org_a_headers, "Org A's Source")

    org_b_headers = _auth_headers(
        await register_and_login(
            email="doc-org-b@example.com", organization_name="Doc Org B"
        )
    )
    response = await client.post(
        DOC_BASE,
        json={"knowledge_source_id": ks_id, "name": "Smuggled.pdf"},
        headers=org_b_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_documents_filtered_by_knowledge_source(
    client: AsyncClient, register_and_login
) -> None:
    headers = _auth_headers(await register_and_login(email="doc3@example.com"))
    ks_id = await _create_knowledge_source(client, headers, "Filter Source")
    other_ks_id = await _create_knowledge_source(client, headers, "Other Source")

    await client.post(
        DOC_BASE, json={"knowledge_source_id": ks_id, "name": "In Scope.pdf"}, headers=headers
    )
    await client.post(
        DOC_BASE,
        json={"knowledge_source_id": other_ks_id, "name": "Out Of Scope.pdf"},
        headers=headers,
    )

    response = await client.get(
        DOC_BASE, params={"knowledge_source_id": ks_id}, headers=headers
    )
    assert response.status_code == 200
    names = [doc["name"] for doc in response.json()]
    assert names == ["In Scope.pdf"]


@pytest.mark.asyncio
async def test_new_user_sees_zero_documents_despite_other_orgs_having_some(
    client: AsyncClient, register_and_login
) -> None:
    """Direct regression test for the reported bug, same as copilots/
    knowledge sources: documents are scoped transitively through their
    knowledge source's organization, and a brand-new org must see none
    of another organization's documents.
    """
    other_org_headers = _auth_headers(
        await register_and_login(
            email="doc-other-org@example.com", organization_name="Doc Other Org"
        )
    )
    other_ks_id = await _create_knowledge_source(client, other_org_headers, "Other Org Source")
    await client.post(
        DOC_BASE,
        json={"knowledge_source_id": other_ks_id, "name": "Other Org's Doc.pdf"},
        headers=other_org_headers,
    )

    new_user_headers = _auth_headers(
        await register_and_login(
            email="doc-new-user@example.com", organization_name="Doc Brand New Org"
        )
    )
    response = await client.get(DOC_BASE, headers=new_user_headers)
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_document_not_found(client: AsyncClient, register_and_login) -> None:
    headers = _auth_headers(await register_and_login(email="doc4@example.com"))
    response = await client.get(
        f"{DOC_BASE}/00000000-0000-0000-0000-000000000000", headers=headers
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_cannot_get_another_organizations_document(
    client: AsyncClient, register_and_login
) -> None:
    org_a_headers = _auth_headers(
        await register_and_login(
            email="doc-get-org-a@example.com", organization_name="Doc Get Org A"
        )
    )
    ks_id = await _create_knowledge_source(client, org_a_headers, "Get Org A Source")
    created = (
        await client.post(
            DOC_BASE,
            json={"knowledge_source_id": ks_id, "name": "Org A's Doc.pdf"},
            headers=org_a_headers,
        )
    ).json()

    org_b_headers = _auth_headers(
        await register_and_login(
            email="doc-get-org-b@example.com", organization_name="Doc Get Org B"
        )
    )
    response = await client.get(f"{DOC_BASE}/{created['id']}", headers=org_b_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_document(client: AsyncClient, register_and_login) -> None:
    headers = _auth_headers(await register_and_login(email="doc5@example.com"))
    ks_id = await _create_knowledge_source(client, headers, "Delete Doc Source")
    created = (
        await client.post(
            DOC_BASE, json={"knowledge_source_id": ks_id, "name": "Bye.pdf"}, headers=headers
        )
    ).json()

    delete_response = await client.delete(f"{DOC_BASE}/{created['id']}", headers=headers)
    assert delete_response.status_code == 204

    get_response = await client.get(f"{DOC_BASE}/{created['id']}", headers=headers)
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_deleting_knowledge_source_cascades_to_documents(
    client: AsyncClient, register_and_login
) -> None:
    headers = _auth_headers(await register_and_login(email="doc6@example.com"))
    ks_id = await _create_knowledge_source(client, headers, "Cascade Source")
    created = (
        await client.post(
            DOC_BASE,
            json={"knowledge_source_id": ks_id, "name": "Cascaded.pdf"},
            headers=headers,
        )
    ).json()

    await client.delete(f"{KS_BASE}/{ks_id}", headers=headers)

    response = await client.get(f"{DOC_BASE}/{created['id']}", headers=headers)
    assert response.status_code == 404
