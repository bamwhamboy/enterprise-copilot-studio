"""Tests for /api/v1/copilots."""

import pytest
from httpx import AsyncClient

KS_BASE = "/api/v1/knowledge-sources"
COPILOT_BASE = "/api/v1/copilots"


def _auth_headers(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _create_knowledge_source(
    client: AsyncClient, headers: dict, name: str = "Copilot Test Source"
) -> str:
    response = await client.post(KS_BASE, json={"name": name}, headers=headers)
    return response.json()["id"]


@pytest.mark.asyncio
async def test_create_copilot_minimal(client: AsyncClient, register_and_login) -> None:
    headers = _auth_headers(await register_and_login(email="copilot1@example.com"))
    response = await client.post(
        COPILOT_BASE, json={"name": "Minimal Copilot"}, headers=headers
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Minimal Copilot"
    assert body["domain"] == "hr"
    assert body["status"] == "draft"
    assert body["model"] == "openai/gpt-oss-120b"
    assert body["knowledge_sources"] == []


@pytest.mark.asyncio
async def test_create_copilot_requires_auth(client: AsyncClient) -> None:
    response = await client.post(COPILOT_BASE, json={"name": "No Auth Copilot"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_copilot_missing_name_returns_422(
    client: AsyncClient, register_and_login
) -> None:
    headers = _auth_headers(await register_and_login(email="copilot2@example.com"))
    response = await client.post(COPILOT_BASE, json={"domain": "hr"}, headers=headers)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_copilot_existing_domains_still_work(
    client: AsyncClient, register_and_login
) -> None:
    """The previously-fixed domains must still work now that domain is
    free-form -- this isn't special-cased, it's just any valid string."""
    headers = _auth_headers(await register_and_login(email="copilot3@example.com"))
    for domain in ("hr", "finance", "procurement", "sales", "legal", "it", "analytics"):
        response = await client.post(
            COPILOT_BASE, json={"name": f"{domain} copilot", "domain": domain}, headers=headers
        )
        assert response.status_code == 201, response.text
        assert response.json()["domain"] == domain


@pytest.mark.asyncio
async def test_create_copilot_custom_domain_is_accepted_and_normalized(
    client: AsyncClient, register_and_login
) -> None:
    headers = _auth_headers(await register_and_login(email="copilot3b@example.com"))
    response = await client.post(
        COPILOT_BASE,
        json={"name": "Clinical Copilot", "domain": "  Clinical Research  "},
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["domain"] == "clinical research"


@pytest.mark.asyncio
async def test_create_copilot_empty_domain_returns_422(
    client: AsyncClient, register_and_login
) -> None:
    headers = _auth_headers(await register_and_login(email="copilot3c@example.com"))
    response = await client.post(
        COPILOT_BASE, json={"name": "X", "domain": "   "}, headers=headers
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_copilot_domain_too_long_returns_422(
    client: AsyncClient, register_and_login
) -> None:
    headers = _auth_headers(await register_and_login(email="copilot3d@example.com"))
    response = await client.post(
        COPILOT_BASE, json={"name": "X", "domain": "a" * 101}, headers=headers
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_copilot_accepts_custom_domain(
    client: AsyncClient, register_and_login
) -> None:
    headers = _auth_headers(await register_and_login(email="copilot3e@example.com"))
    create_response = await client.post(
        COPILOT_BASE, json={"name": "Retitle Me"}, headers=headers
    )
    copilot_id = create_response.json()["id"]

    response = await client.put(
        f"{COPILOT_BASE}/{copilot_id}",
        json={"domain": "  Regulatory Affairs  "},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["domain"] == "regulatory affairs"


@pytest.mark.asyncio
async def test_create_copilot_with_knowledge_sources(
    client: AsyncClient, register_and_login
) -> None:
    headers = _auth_headers(await register_and_login(email="copilot4@example.com"))
    ks_id = await _create_knowledge_source(client, headers, "Attached Source")
    response = await client.post(
        COPILOT_BASE,
        json={"name": "HR Copilot", "knowledge_source_ids": [ks_id]},
        headers=headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert len(body["knowledge_sources"]) == 1
    assert body["knowledge_sources"][0]["id"] == ks_id


@pytest.mark.asyncio
async def test_list_copilots(client: AsyncClient, register_and_login) -> None:
    headers = _auth_headers(await register_and_login(email="copilot5@example.com"))
    await client.post(COPILOT_BASE, json={"name": "Listed Copilot"}, headers=headers)
    response = await client.get(COPILOT_BASE, headers=headers)
    assert response.status_code == 200
    names = [c["name"] for c in response.json()]
    assert "Listed Copilot" in names


@pytest.mark.asyncio
async def test_list_copilots_requires_auth(client: AsyncClient) -> None:
    response = await client.get(COPILOT_BASE)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_new_user_sees_zero_copilots_despite_other_orgs_having_some(
    client: AsyncClient, register_and_login
) -> None:
    """Direct regression test for the reported bug: a brand-new user in a
    brand-new organization must see 0 copilots on GET /copilots, even
    though other organizations have created copilots of their own.
    """
    other_org_headers = _auth_headers(
        await register_and_login(
            email="other-org-owner@example.com", organization_name="Other Org"
        )
    )
    await client.post(
        COPILOT_BASE, json={"name": "Other Org's Copilot"}, headers=other_org_headers
    )

    new_user_headers = _auth_headers(
        await register_and_login(
            email="brand-new-user@example.com", organization_name="Brand New Org"
        )
    )
    response = await client.get(COPILOT_BASE, headers=new_user_headers)
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_cannot_get_another_organizations_copilot_by_id(
    client: AsyncClient, register_and_login
) -> None:
    """Direct object reference check: even knowing another org's copilot
    id shouldn't allow fetching it -- should 404, not reveal its data.
    """
    org_a_headers = _auth_headers(
        await register_and_login(email="org-a@example.com", organization_name="Org A")
    )
    created = (
        await client.post(COPILOT_BASE, json={"name": "Org A's Copilot"}, headers=org_a_headers)
    ).json()

    org_b_headers = _auth_headers(
        await register_and_login(email="org-b@example.com", organization_name="Org B")
    )
    response = await client.get(f"{COPILOT_BASE}/{created['id']}", headers=org_b_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_copilot_not_found(client: AsyncClient, register_and_login) -> None:
    headers = _auth_headers(await register_and_login(email="copilot6@example.com"))
    response = await client.get(
        f"{COPILOT_BASE}/00000000-0000-0000-0000-000000000000", headers=headers
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_update_copilot_fields(client: AsyncClient, register_and_login) -> None:
    headers = _auth_headers(await register_and_login(email="copilot7@example.com"))
    created = (
        await client.post(COPILOT_BASE, json={"name": "Draft Copilot"}, headers=headers)
    ).json()

    response = await client.put(
        f"{COPILOT_BASE}/{created['id']}",
        json={"status": "active", "model": "groq-llama-3-70b"},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "active"
    assert body["model"] == "groq-llama-3-70b"
    assert body["name"] == "Draft Copilot"  # untouched fields preserved


@pytest.mark.asyncio
async def test_cannot_update_another_organizations_copilot(
    client: AsyncClient, register_and_login
) -> None:
    org_a_headers = _auth_headers(
        await register_and_login(
            email="update-org-a@example.com", organization_name="Update Org A"
        )
    )
    created = (
        await client.post(
            COPILOT_BASE, json={"name": "Protected Copilot"}, headers=org_a_headers
        )
    ).json()

    org_b_headers = _auth_headers(
        await register_and_login(
            email="update-org-b@example.com", organization_name="Update Org B"
        )
    )
    response = await client.put(
        f"{COPILOT_BASE}/{created['id']}", json={"status": "active"}, headers=org_b_headers
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_copilot_replaces_knowledge_sources(
    client: AsyncClient, register_and_login
) -> None:
    headers = _auth_headers(await register_and_login(email="copilot8@example.com"))
    ks_a = await _create_knowledge_source(client, headers, "Source A")
    ks_b = await _create_knowledge_source(client, headers, "Source B")

    created = (
        await client.post(
            COPILOT_BASE,
            json={"name": "Rewireable Copilot", "knowledge_source_ids": [ks_a]},
            headers=headers,
        )
    ).json()
    assert [ks["id"] for ks in created["knowledge_sources"]] == [ks_a]

    updated = (
        await client.put(
            f"{COPILOT_BASE}/{created['id']}",
            json={"knowledge_source_ids": [ks_b]},
            headers=headers,
        )
    ).json()
    assert [ks["id"] for ks in updated["knowledge_sources"]] == [ks_b]


@pytest.mark.asyncio
async def test_delete_copilot(client: AsyncClient, register_and_login) -> None:
    headers = _auth_headers(await register_and_login(email="copilot9@example.com"))
    created = (
        await client.post(COPILOT_BASE, json={"name": "Deletable Copilot"}, headers=headers)
    ).json()

    delete_response = await client.delete(f"{COPILOT_BASE}/{created['id']}", headers=headers)
    assert delete_response.status_code == 204

    get_response = await client.get(f"{COPILOT_BASE}/{created['id']}", headers=headers)
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_cannot_delete_another_organizations_copilot(
    client: AsyncClient, register_and_login
) -> None:
    org_a_headers = _auth_headers(
        await register_and_login(
            email="delete-org-a@example.com", organization_name="Delete Org A"
        )
    )
    created = (
        await client.post(
            COPILOT_BASE, json={"name": "Undeletable-by-others"}, headers=org_a_headers
        )
    ).json()

    org_b_headers = _auth_headers(
        await register_and_login(
            email="delete-org-b@example.com", organization_name="Delete Org B"
        )
    )
    response = await client.delete(f"{COPILOT_BASE}/{created['id']}", headers=org_b_headers)
    assert response.status_code == 404

    # Confirm it's still there from its actual owner's perspective.
    still_there = await client.get(f"{COPILOT_BASE}/{created['id']}", headers=org_a_headers)
    assert still_there.status_code == 200


@pytest.mark.asyncio
async def test_deleting_copilot_does_not_delete_knowledge_source(
    client: AsyncClient, register_and_login
) -> None:
    headers = _auth_headers(await register_and_login(email="copilot10@example.com"))
    ks_id = await _create_knowledge_source(client, headers, "Surviving Source")
    created = (
        await client.post(
            COPILOT_BASE,
            json={"name": "Ephemeral Copilot", "knowledge_source_ids": [ks_id]},
            headers=headers,
        )
    ).json()

    await client.delete(f"{COPILOT_BASE}/{created['id']}", headers=headers)

    response = await client.get(f"{KS_BASE}/{ks_id}", headers=headers)
    assert response.status_code == 200


# --- Capabilities / HITL foundation (Sprint 1) ------------------------------


@pytest.mark.asyncio
async def test_create_copilot_defaults_to_human_in_the_loop_disabled(
    client: AsyncClient, register_and_login
) -> None:
    headers = _auth_headers(await register_and_login(email="copilot-cap1@example.com"))
    response = await client.post(
        COPILOT_BASE, json={"name": "Default Capabilities Copilot"}, headers=headers
    )
    assert response.status_code == 201
    assert response.json()["capabilities"] == {"human_in_the_loop": False}


@pytest.mark.asyncio
async def test_create_copilot_with_explicit_human_in_the_loop_true(
    client: AsyncClient, register_and_login
) -> None:
    headers = _auth_headers(await register_and_login(email="copilot-cap2@example.com"))
    response = await client.post(
        COPILOT_BASE,
        json={"name": "HITL Copilot", "capabilities": {"human_in_the_loop": True}},
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["capabilities"] == {"human_in_the_loop": True}


@pytest.mark.asyncio
async def test_create_copilot_capabilities_allows_future_extra_keys(
    client: AsyncClient, register_and_login
) -> None:
    """A not-yet-named capability key (e.g. a future retrieval/graph/
    agentic toggle) must not be rejected -- it's carried through
    opaquely until it's promoted to a real field."""
    headers = _auth_headers(await register_and_login(email="copilot-cap3@example.com"))
    response = await client.post(
        COPILOT_BASE,
        json={
            "name": "Forward Compatible Copilot",
            "capabilities": {"human_in_the_loop": False, "future_toggle": True},
        },
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["capabilities"] == {
        "human_in_the_loop": False,
        "future_toggle": True,
    }


@pytest.mark.asyncio
async def test_create_copilot_rejects_non_bool_human_in_the_loop(
    client: AsyncClient, register_and_login
) -> None:
    headers = _auth_headers(await register_and_login(email="copilot-cap4@example.com"))
    response = await client.post(
        COPILOT_BASE,
        json={"name": "X", "capabilities": {"human_in_the_loop": "not-a-bool"}},
        headers=headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_copilot_rejects_non_object_capabilities(
    client: AsyncClient, register_and_login
) -> None:
    headers = _auth_headers(await register_and_login(email="copilot-cap5@example.com"))
    response = await client.post(
        COPILOT_BASE,
        json={"name": "X", "capabilities": "not-an-object"},
        headers=headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_copilot_toggles_human_in_the_loop(
    client: AsyncClient, register_and_login
) -> None:
    headers = _auth_headers(await register_and_login(email="copilot-cap6@example.com"))
    created = (
        await client.post(COPILOT_BASE, json={"name": "Toggle Me"}, headers=headers)
    ).json()
    assert created["capabilities"] == {"human_in_the_loop": False}

    response = await client.put(
        f"{COPILOT_BASE}/{created['id']}",
        json={"capabilities": {"human_in_the_loop": True}},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["capabilities"] == {"human_in_the_loop": True}


@pytest.mark.asyncio
async def test_update_without_capabilities_leaves_existing_value_unchanged(
    client: AsyncClient, register_and_login
) -> None:
    """Omitting capabilities on update must not reset it -- standard
    partial-update semantics (exclude_unset), same as every other
    optional field on this schema."""
    headers = _auth_headers(await register_and_login(email="copilot-cap7@example.com"))
    created = (
        await client.post(
            COPILOT_BASE,
            json={"name": "Untouched Capabilities", "capabilities": {"human_in_the_loop": True}},
            headers=headers,
        )
    ).json()

    response = await client.put(
        f"{COPILOT_BASE}/{created['id']}", json={"name": "Renamed"}, headers=headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Renamed"
    assert body["capabilities"] == {"human_in_the_loop": True}


@pytest.mark.asyncio
async def test_update_copilot_rejects_non_bool_human_in_the_loop(
    client: AsyncClient, register_and_login
) -> None:
    headers = _auth_headers(await register_and_login(email="copilot-cap8@example.com"))
    created = (
        await client.post(COPILOT_BASE, json={"name": "X"}, headers=headers)
    ).json()

    response = await client.put(
        f"{COPILOT_BASE}/{created['id']}",
        json={"capabilities": {"human_in_the_loop": 12345}},
        headers=headers,
    )
    assert response.status_code == 422
