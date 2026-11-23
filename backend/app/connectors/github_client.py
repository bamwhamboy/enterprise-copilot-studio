"""Minimal GitHub API client for validating repository access."""

from dataclasses import dataclass

import httpx


GITHUB_API = "https://api.github.com"


class GitHubAPIError(Exception):
    """Raised when GitHub rejects a request or returns an unexpected response."""


@dataclass(frozen=True)
class GitHubRepository:
    owner: str
    name: str
    full_name: str
    default_branch: str
    private: bool


async def validate_repository_access(
    token: str,
    owner: str,
    repository: str,
) -> GitHubRepository:
    """Validate a token and confirm it can access the requested repository."""
    if not token.strip() or not owner.strip() or not repository.strip():
        raise ValueError("GitHub token, owner, and repository are required.")

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    try:
        async with httpx.AsyncClient(
            base_url=GITHUB_API,
            headers=headers,
            timeout=15.0,
            follow_redirects=False,
        ) as client:
            response = await client.get(
                f"/repos/{owner.strip()}/{repository.strip()}"
            )
    except httpx.HTTPError as exc:
        raise GitHubAPIError("Could not reach GitHub to validate repository access.") from exc

    if response.status_code == 401:
        raise GitHubAPIError("GitHub token is invalid or expired.")
    if response.status_code == 403:
        message = response.json().get("message", "Permission denied.")
        raise GitHubAPIError(f"GitHub permission error: {message}")
    if response.status_code == 404:
        raise GitHubAPIError(
            "Repository not found or token does not have access to it."
        )

    if response.status_code != 200:
        raise GitHubAPIError(
            f"GitHub repository validation failed with HTTP {response.status_code}."
        )

    try:
        data = response.json()
        return GitHubRepository(
            owner=data["owner"]["login"],
            name=data["name"],
            full_name=data["full_name"],
            default_branch=data["default_branch"],
            private=bool(data["private"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise GitHubAPIError("GitHub returned an invalid repository response.") from exc
