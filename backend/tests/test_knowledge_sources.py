"""Tests for /api/v1/knowledge-sources."""

import pytest
from httpx import AsyncClient

BASE = "/api/v1/knowledge-sources"


def _auth_headers(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


@pytest.mark.asyncio
async def test_create_knowledge_source(client: AsyncClient, register_and_login) -> None:
    headers = _auth_headers(await register_and_login(email="ks1@example.com"))
    response = await client.post(
        BASE,
        json={"name": "Finance Docs", "source_type": "documents", "status": "active"},
        headers=headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Finance Docs"
    assert body["documents"] == []


@pytest.mark.asyncio
async def test_create_knowledge_source_requires_auth(client: AsyncClient) -> None:
    response = await client.post(BASE, json={"name": "No Auth Source"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_knowledge_source_defaults(client: AsyncClient, register_and_login) -> None:
    headers = _auth_headers(await register_and_login(email="ks2@example.com"))
    response = await client.post(BASE, json={"name": "Defaults Source"}, headers=headers)
    assert response.status_code == 201
    body = response.json()
    assert body["source_type"] == "documents"
    assert body["status"] == "active"


@pytest.mark.asyncio
async def test_list_knowledge_sources(client: AsyncClient, register_and_login) -> None:
    headers = _auth_headers(await register_and_login(email="ks3@example.com"))
    await client.post(BASE, json={"name": "Listed Source"}, headers=headers)
    response = await client.get(BASE, headers=headers)
    assert response.status_code == 200
    names = [ks["name"] for ks in response.json()]
    assert "Listed Source" in names


@pytest.mark.asyncio
async def test_list_knowledge_sources_requires_auth(client: AsyncClient) -> None:
    response = await client.get(BASE)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_new_user_sees_zero_knowledge_sources_despite_other_orgs_having_some(
    client: AsyncClient, register_and_login
) -> None:
    """Direct regression test for the reported bug, same as the copilots
    version: a brand-new organization's dashboard must show 0 knowledge
    sources, not another organization's count.
    """
    other_org_headers = _auth_headers(
        await register_and_login(
            email="ks-other-org@example.com", organization_name="KS Other Org"
        )
    )
    await client.post(BASE, json={"name": "Other Org's Source"}, headers=other_org_headers)

    new_user_headers = _auth_headers(
        await register_and_login(
            email="ks-new-user@example.com", organization_name="KS Brand New Org"
        )
    )
    response = await client.get(BASE, headers=new_user_headers)
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_knowledge_source(client: AsyncClient, register_and_login) -> None:
    headers = _auth_headers(await register_and_login(email="ks4@example.com"))
    created = (
        await client.post(BASE, json={"name": "Gettable Source"}, headers=headers)
    ).json()
    response = await client.get(f"{BASE}/{created['id']}", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


@pytest.mark.asyncio
async def test_cannot_get_another_organizations_knowledge_source(
    client: AsyncClient, register_and_login
) -> None:
    org_a_headers = _auth_headers(
        await register_and_login(email="ks-org-a@example.com", organization_name="KS Org A")
    )
    created = (
        await client.post(BASE, json={"name": "Org A's Source"}, headers=org_a_headers)
    ).json()

    org_b_headers = _auth_headers(
        await register_and_login(email="ks-org-b@example.com", organization_name="KS Org B")
    )
    response = await client.get(f"{BASE}/{created['id']}", headers=org_b_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_knowledge_source_not_found(client: AsyncClient, register_and_login) -> None:
    headers = _auth_headers(await register_and_login(email="ks5@example.com"))
    response = await client.get(
        f"{BASE}/00000000-0000-0000-0000-000000000000", headers=headers
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_knowledge_source(client: AsyncClient, register_and_login) -> None:
    headers = _auth_headers(await register_and_login(email="ks6@example.com"))
    created = (await client.post(BASE, json={"name": "Old Name"}, headers=headers)).json()
    response = await client.put(
        f"{BASE}/{created['id']}", json={"name": "New Name"}, headers=headers
    )
    assert response.status_code == 200
    assert response.json()["name"] == "New Name"


@pytest.mark.asyncio
async def test_cannot_update_another_organizations_knowledge_source(
    client: AsyncClient, register_and_login
) -> None:
    org_a_headers = _auth_headers(
        await register_and_login(
            email="ks-update-org-a@example.com", organization_name="KS Update Org A"
        )
    )
    created = (
        await client.post(BASE, json={"name": "Protected Source"}, headers=org_a_headers)
    ).json()

    org_b_headers = _auth_headers(
        await register_and_login(
            email="ks-update-org-b@example.com", organization_name="KS Update Org B"
        )
    )
    response = await client.put(
        f"{BASE}/{created['id']}", json={"name": "Hijacked Name"}, headers=org_b_headers
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_knowledge_source(client: AsyncClient, register_and_login) -> None:
    headers = _auth_headers(await register_and_login(email="ks7@example.com"))
    created = (
        await client.post(BASE, json={"name": "Deletable Source"}, headers=headers)
    ).json()
    delete_response = await client.delete(f"{BASE}/{created['id']}", headers=headers)
    assert delete_response.status_code == 204

    get_response = await client.get(f"{BASE}/{created['id']}", headers=headers)
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_cannot_delete_another_organizations_knowledge_source(
    client: AsyncClient, register_and_login
) -> None:
    org_a_headers = _auth_headers(
        await register_and_login(
            email="ks-delete-org-a@example.com", organization_name="KS Delete Org A"
        )
    )
    created = (
        await client.post(
            BASE, json={"name": "Undeletable-by-others"}, headers=org_a_headers
        )
    ).json()

    org_b_headers = _auth_headers(
        await register_and_login(
            email="ks-delete-org-b@example.com", organization_name="KS Delete Org B"
        )
    )
    response = await client.delete(f"{BASE}/{created['id']}", headers=org_b_headers)
    assert response.status_code == 404

    still_there = await client.get(f"{BASE}/{created['id']}", headers=org_a_headers)
    assert still_there.status_code == 200


@pytest.mark.asyncio
async def test_create_knowledge_source_invalid_type(
    client: AsyncClient, register_and_login
) -> None:
    headers = _auth_headers(await register_and_login(email="ks8@example.com"))
    response = await client.post(
        BASE, json={"name": "Bad Type", "source_type": "carrier-pigeon"}, headers=headers
    )
    assert response.status_code == 422
