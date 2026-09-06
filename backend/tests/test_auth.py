"""Tests for authentication & authorization (Sprint 6)."""

import pytest
from httpx import AsyncClient

from app.llm.providers import LLMProvider, to_litellm_model

AUTH_BASE = "/api/v1/auth"


@pytest.mark.asyncio
async def test_register_creates_new_org_and_admin_role(client: AsyncClient) -> None:
    response = await client.post(
        f"{AUTH_BASE}/register",
        json={
            "email": "founder@newco.com",
            "password": "SecurePass123",
            "organization_name": "NewCo",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "founder@newco.com"
    assert body["role"]["name"] == "organization_admin"
    assert body["is_active"] is True


@pytest.mark.asyncio
async def test_register_second_user_joins_existing_org_as_end_user(client: AsyncClient) -> None:
    first = (
        await client.post(
            f"{AUTH_BASE}/register",
            json={
                "email": "a@sharedorg.com",
                "password": "SecurePass123",
                "organization_name": "Shared Org",
            },
        )
    ).json()
    second = (
        await client.post(
            f"{AUTH_BASE}/register",
            json={
                "email": "b@sharedorg.com",
                "password": "SecurePass123",
                "organization_name": "Shared Org",
            },
        )
    ).json()

    assert second["role"]["name"] == "end_user"
    assert second["organization_id"] == first["organization_id"]


@pytest.mark.asyncio
async def test_register_duplicate_email_returns_401(client: AsyncClient) -> None:
    payload = {
        "email": "dupe@test.com",
        "password": "SecurePass123",
        "organization_name": "Dupe Org",
    }
    await client.post(f"{AUTH_BASE}/register", json=payload)
    response = await client.post(f"{AUTH_BASE}/register", json=payload)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_returns_valid_tokens(client: AsyncClient) -> None:
    await client.post(
        f"{AUTH_BASE}/register",
        json={
            "email": "login@test.com",
            "password": "SecurePass123",
            "organization_name": "Login Org",
        },
    )
    response = await client.post(
        f"{AUTH_BASE}/login", data={"username": "login@test.com", "password": "SecurePass123"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0
    assert body["access_token"]
    assert body["refresh_token"]


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401(client: AsyncClient) -> None:
    await client.post(
        f"{AUTH_BASE}/register",
        json={
            "email": "wrongpw@test.com",
            "password": "SecurePass123",
            "organization_name": "WP Org",
        },
    )
    response = await client.post(
        f"{AUTH_BASE}/login",
        data={"username": "wrongpw@test.com", "password": "IncorrectPassword"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user_returns_401(client: AsyncClient) -> None:
    response = await client.post(
        f"{AUTH_BASE}/login", data={"username": "nobody@nowhere.com", "password": "whatever123"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_requires_authentication(client: AsyncClient) -> None:
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_returns_authenticated_user(client: AsyncClient, register_and_login) -> None:
    tokens = await register_and_login(email="me@test.com")
    response = await client.get(
        "/api/v1/users/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == "me@test.com"


@pytest.mark.asyncio
async def test_get_me_with_invalid_token_returns_401(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/users/me", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_rotates_token_and_old_one_becomes_invalid(
    client: AsyncClient, register_and_login
) -> None:
    tokens = await register_and_login(email="rotate@test.com")

    refreshed = await client.post(
        f"{AUTH_BASE}/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refreshed.status_code == 200
    new_tokens = refreshed.json()
    assert new_tokens["refresh_token"] != tokens["refresh_token"]

    replay = await client.post(
        f"{AUTH_BASE}/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert replay.status_code == 401


@pytest.mark.asyncio
async def test_refresh_with_garbage_token_returns_401(client: AsyncClient) -> None:
    response = await client.post(f"{AUTH_BASE}/refresh", json={"refresh_token": "garbage"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout_revokes_refresh_token(client: AsyncClient, register_and_login) -> None:
    tokens = await register_and_login(email="logout@test.com")

    logout_response = await client.post(
        f"{AUTH_BASE}/logout", json={"refresh_token": tokens["refresh_token"]}
    )
    assert logout_response.status_code == 204

    reuse_response = await client.post(
        f"{AUTH_BASE}/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert reuse_response.status_code == 401


@pytest.mark.asyncio
async def test_logout_with_unknown_token_is_idempotent(client: AsyncClient) -> None:
    response = await client.post(f"{AUTH_BASE}/logout", json={"refresh_token": "never-issued"})
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_list_roles_returns_all_five(client: AsyncClient, register_and_login) -> None:
    tokens = await register_and_login(email="roles@test.com")
    response = await client.get(
        "/api/v1/roles", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert response.status_code == 200
    role_names = {r["name"] for r in response.json()}
    assert role_names == {
        "super_admin",
        "organization_admin",
        "copilot_creator",
        "knowledge_manager",
        "end_user",
    }


@pytest.mark.asyncio
async def test_list_organizations_scoped_to_own_org_for_non_super_admin(
    client: AsyncClient, register_and_login
) -> None:
    tokens = await register_and_login(email="orgscope@test.com", organization_name="Scoped Org")
    response = await client.get(
        "/api/v1/organizations", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert response.status_code == 200
    orgs = response.json()
    assert len(orgs) == 1
    assert orgs[0]["name"] == "Scoped Org"


def test_groq_prefixes_openai_style_model_name():
    assert (
        to_litellm_model(LLMProvider.GROQ, "openai/gpt-oss-120b")
        == "groq/openai/gpt-oss-120b"
    )


def test_groq_prefixes_bare_model_name():
    assert (
        to_litellm_model(LLMProvider.GROQ, "gpt-oss-120b")
        == "groq/gpt-oss-120b"
    )


def test_groq_does_not_double_prefix_already_qualified_model():
    assert (
        to_litellm_model(
            LLMProvider.GROQ,
            "groq/openai/gpt-oss-120b",
        )
        == "groq/openai/gpt-oss-120b"
    )


def test_openai_model_unchanged():
    assert to_litellm_model(LLMProvider.OPENAI, "gpt-4o") == "gpt-4o"
