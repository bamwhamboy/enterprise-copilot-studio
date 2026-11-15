"""API tests for GitHub knowledge-source connections."""

import pytest

from httpx import AsyncClient

from app.connectors.github_client import GitHubRepository

BASE = "/api/v1/knowledge-sources"


def auth(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def create_source(client: AsyncClient, headers: dict) -> str:
    response = await client.post(
        BASE,
        json={"name": "GitHub Test Source", "source_type": "connector"},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def mock_github(monkeypatch):
    """Avoid external GitHub calls while exercising the real API and DB."""
    async def fake_validate(token, owner, repository):
        assert token == "test-github-token"
        return GitHubRepository(
            owner=owner,
            name=repository,
            full_name=f"{owner}/{repository}",
            default_branch="main",
            private=True,
        )

    monkeypatch.setattr(
        "app.services.github_connection_service.validate_repository_access",
        fake_validate,
    )
    monkeypatch.setattr(
        "app.services.github_connection_service.encrypt_credential",
        lambda token: "encrypted-test-token",
    )


@pytest.mark.asyncio
async def test_github_connection_requires_authentication(
    client: AsyncClient,
):
    response = await client.get(f"{BASE}/00000000-0000-0000-0000-000000000001/github")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_connect_and_read_github_connection(
    client: AsyncClient, register_and_login, monkeypatch,
):
    mock_github(monkeypatch)

    tokens = await register_and_login(email="github-connect@example.com")
    headers = auth(tokens)
    source_id = await create_source(client, headers)

    response = await client.post(
        f"{BASE}/{source_id}/github",
        headers=headers,
        json={
            "repository_owner": "example-org",
            "repository_name": "example-repo",
            "token": "test-github-token",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["repository_owner"] == "example-org"
    assert body["repository_name"] == "example-repo"
    assert body["sync_status"] == "pending"
    assert "token" not in body
    assert "encrypted_token" not in body
    assert "test-github-token" not in response.text

    read_response = await client.get(
        f"{BASE}/{source_id}/github", headers=headers
    )
    assert read_response.status_code == 200
    assert read_response.json()["id"] == body["id"]
    assert "encrypted_token" not in read_response.json()


@pytest.mark.asyncio
async def test_duplicate_github_connection_returns_conflict(
    client: AsyncClient, register_and_login, monkeypatch,
):
    mock_github(monkeypatch)

    tokens = await register_and_login(email="github-duplicate@example.com")
    headers = auth(tokens)
    source_id = await create_source(client, headers)

    payload = {
        "repository_owner": "example-org",
        "repository_name": "example-repo",
        "token": "test-github-token",
    }

    first = await client.post(
        f"{BASE}/{source_id}/github", headers=headers, json=payload
    )
    second = await client.post(
        f"{BASE}/{source_id}/github", headers=headers, json=payload
    )

    assert first.status_code == 201
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_other_organization_cannot_access_github_connection(
    client: AsyncClient, register_and_login, monkeypatch,
):
    mock_github(monkeypatch)

    owner_tokens = await register_and_login(
        email="github-owner@example.com",
        organization_name="GitHub Owner Org",
    )
    other_tokens = await register_and_login(
        email="github-other@example.com",
        organization_name="GitHub Other Org",
    )

    owner_headers = auth(owner_tokens)
    other_headers = auth(other_tokens)
    source_id = await create_source(client, owner_headers)

    response = await client.post(
        f"{BASE}/{source_id}/github",
        headers=other_headers,
        json={
            "repository_owner": "example-org",
            "repository_name": "example-repo",
            "token": "test-github-token",
        },
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_disconnect_github_connection(
    client: AsyncClient, register_and_login, monkeypatch,
):
    mock_github(monkeypatch)

    tokens = await register_and_login(email="github-disconnect@example.com")
    headers = auth(tokens)
    source_id = await create_source(client, headers)

    connect_response = await client.post(
        f"{BASE}/{source_id}/github",
        headers=headers,
        json={
            "repository_owner": "example-org",
            "repository_name": "example-repo",
            "token": "test-github-token",
        },
    )
    assert connect_response.status_code == 201

    delete_response = await client.delete(
        f"{BASE}/{source_id}/github", headers=headers
    )
    assert delete_response.status_code == 204

    read_response = await client.get(
        f"{BASE}/{source_id}/github", headers=headers
    )
    assert read_response.status_code == 404
