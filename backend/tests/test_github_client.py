import httpx
import pytest

from app.connectors.github_client import (
    GitHubAPIError,
    validate_repository_access,
)


@pytest.mark.asyncio
async def test_validate_repository_access_success(monkeypatch):
    original_async_client = httpx.AsyncClient

    def handler(request):
        assert request.url.path == "/repos/acme/platform-docs"
        assert request.headers["Authorization"] == "Bearer test-token"
        return httpx.Response(
            200,
            json={
                "owner": {"login": "acme"},
                "name": "platform-docs",
                "full_name": "acme/platform-docs",
                "default_branch": "main",
                "private": True,
            },
        )

    def mock_async_client(**kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return original_async_client(**kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", mock_async_client)

    result = await validate_repository_access(
        "test-token", "acme", "platform-docs"
    )
    assert result.full_name == "acme/platform-docs"
    assert result.default_branch == "main"
    assert result.private is True


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [401, 403, 404])
async def test_access_denied_or_repository_unavailable(monkeypatch, status_code):
    original_async_client = httpx.AsyncClient
    def handler(request):
        return httpx.Response(status_code, json={"message": "unavailable"})

    def mock_async_client(**kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return original_async_client(**kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", mock_async_client)

    with pytest.raises(GitHubAPIError, match="rejected the token"):
        await validate_repository_access("test-token", "acme", "private-repo")


@pytest.mark.asyncio
async def test_empty_credentials_rejected():
    with pytest.raises(ValueError, match="required"):
        await validate_repository_access("", "acme", "repo")
