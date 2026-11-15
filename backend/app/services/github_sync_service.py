"""Synchronize supported GitHub repository files into the knowledge base."""

import base64
import uuid
from pathlib import PurePosixPath
from urllib.parse import quote

import httpx
from sqlalchemy import select

from app.models.document import Document

from app.connectors.github_client import GITHUB_API, GitHubAPIError
from app.core.config import get_settings
from app.security.credential_encryption import decrypt_credential
from app.services.github_connection_service import GitHubConnectionService

TEXT_EXTENSIONS = {
    ".md", ".py", ".js", ".ts", ".tsx", ".jsx", ".json",
    ".yaml", ".yml", ".toml", ".sql", ".sh", ".html",
    ".css", ".java", ".go", ".rs", ".cs", ".php", ".rb",
    ".xml", ".ini", ".cfg", ".txt",
}

DOCUMENT_EXTENSIONS = {
    ".pdf", ".docx", ".pptx", ".csv", ".xlsx",
}

IGNORED_DIRECTORIES = {
    ".git", "node_modules", "dist", "build", ".venv",
    "venv", "__pycache__", ".next", "coverage",
}

SENSITIVE_NAMES = {
    ".env", ".env.local", ".env.production",
    "id_rsa", "id_ed25519",
}


class GitHubSyncError(Exception):
    """Raised when repository synchronization cannot proceed."""


class GitHubSyncService:
    def __init__(self, session, document_service, indexing_service):
        self.session = session
        self.documents = document_service
        self.indexing = indexing_service
        self.connections = GitHubConnectionService(session)
        self.settings = get_settings()

    @staticmethod
    def _eligible(path: str, size: int, max_bytes: int) -> bool:
        item = PurePosixPath(path)

        if item.is_absolute() or ".." in item.parts:
            return False

        if any(part.lower() in IGNORED_DIRECTORIES for part in item.parts):
            return False

        if item.name.lower() in SENSITIVE_NAMES:
            return False

        if item.suffix.lower() in {".pem", ".key", ".p12", ".pfx"}:
            return False

        return (
            item.suffix.lower() in TEXT_EXTENSIONS | DOCUMENT_EXTENSIONS
            and 0 <= size <= min(max_bytes, 900_000)
        )

    async def _repository_files(self, client, owner, repository, branch, max_bytes):
        branch_path = quote(branch, safe="")
        response = await client.get(
            f"/repos/{owner}/{repository}/git/trees/{branch_path}",
            params={"recursive": "1"},
        )

        if response.status_code != 200:
            raise GitHubAPIError(
                "Could not retrieve the GitHub repository file tree."
            )

        data = response.json()

        if data.get("truncated"):
            raise GitHubSyncError(
                "GitHub returned a truncated repository tree. "
                "This repository needs paginated synchronization."
            )

        return [
            item for item in data.get("tree", [])
            if item.get("type") == "blob"
            and self._eligible(item.get("path", ""), item.get("size", 0), max_bytes)
        ]

    async def _file_content(self, client, owner, repository, path, branch):
        encoded_path = quote(path, safe="/")
        response = await client.get(
            f"/repos/{owner}/{repository}/contents/{encoded_path}",
            params={"ref": branch},
        )

        if response.status_code != 200:
            raise GitHubAPIError("Could not retrieve a repository file.")

        data = response.json()

        if data.get("encoding") != "base64" or not data.get("content"):
            raise GitHubSyncError("GitHub returned an unsupported file encoding.")

        try:
            return base64.b64decode(data["content"])
        except (ValueError, TypeError) as exc:
            raise GitHubSyncError("GitHub returned invalid file content.") from exc

    async def sync(
        self,
        knowledge_source_id: uuid.UUID,
        *,
        organization_id: uuid.UUID | None,
    ) -> dict:
        connection = await self.connections.get_connection(
            knowledge_source_id,
            organization_id=organization_id,
        )

        if connection is None:
            raise GitHubSyncError("No GitHub connection exists for this knowledge source.")

        token = decrypt_credential(connection.encrypted_token)
        owner = connection.repository_owner
        repository = connection.repository_name
        max_bytes = self.settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

        connection.sync_status = "syncing"
        await self.session.commit()

        result = {
            "repository": f"{owner}/{repository}",
            "files_found": 0,
            "files_indexed": 0,
            "files_skipped": 0,
            "files_failed": 0,
            "errors": [],
        }

        try:
            async with httpx.AsyncClient(
                base_url=GITHUB_API,
                headers={
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {token}",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                timeout=30.0,
                follow_redirects=False,
            ) as client:
                repo_response = await client.get(f"/repos/{owner}/{repository}")
                if repo_response.status_code != 200:
                    raise GitHubAPIError(
                        "Could not retrieve GitHub repository metadata."
                    )

                default_branch = repo_response.json().get("default_branch")
                if not default_branch:
                    raise GitHubSyncError(
                        "GitHub repository does not report a default branch."
                    )

                tree = await self._repository_files(
                    client, owner, repository, default_branch, max_bytes
                )

                result["files_found"] = len(tree)

                for item in tree:
                    path = item["path"]

                    try:
                        content = await self._file_content(
                            client, owner, repository, path,
                            default_branch,
                        )

                        if len(content) > max_bytes:
                            result["files_skipped"] += 1
                            continue

                        extension = PurePosixPath(path).suffix.lower()

                        # Existing ParserRegistry supports documents and TXT.
                        # Treat source-code and Markdown files as plain text.
                        filename = (
                            PurePosixPath(path).name
                            if extension in DOCUMENT_EXTENSIONS or extension == ".txt"
                            else PurePosixPath(path).name + ".txt"
                        )

                        existing = await self.session.scalar(
                            select(Document.id).where(
                                Document.knowledge_source_id == knowledge_source_id,
                                Document.original_filename == path,
                            )
                        )
                        if existing:
                            result["files_skipped"] += 1
                            continue

                        document = await self.documents.upload_document(
                            knowledge_source_id=knowledge_source_id,
                            filename=filename,
                            content_type=None,
                            content=content,
                            organization_id=organization_id,
                        )

                        # Retain the repository-relative path for citations.
                        document.name = path[:255]
                        document.original_filename = path[:255]
                        await self.session.commit()

                        await self.indexing.index_document(document.id)
                        result["files_indexed"] += 1

                    except Exception as exc:
                        result["files_failed"] += 1
                        result["errors"].append({
                            "file": path,
                            "error": type(exc).__name__,
                        })

            connection.sync_status = "connected"
            await self.session.commit()
            return result

        except Exception:
            connection.sync_status = "failed"
            await self.session.commit()
            raise
