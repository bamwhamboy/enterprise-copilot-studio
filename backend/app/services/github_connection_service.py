"""Business logic for securely managing GitHub repository connections."""

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.github_client import validate_repository_access
from app.models.github_connection import GitHubConnection
from app.security.credential_encryption import encrypt_credential
from app.services.knowledge_source_service import KnowledgeSourceService


class GitHubConnectionError(Exception):
    """Base exception for GitHub connection operations."""


class GitHubConnectionAlreadyExistsError(GitHubConnectionError):
    """Raised when a knowledge source already has a GitHub connection."""


class GitHubConnectionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.knowledge_sources = KnowledgeSourceService(session)

    async def get_connection(
        self,
        knowledge_source_id: uuid.UUID,
        *,
        organization_id: uuid.UUID | None,
    ) -> GitHubConnection | None:
        await self.knowledge_sources.get_knowledge_source(
            knowledge_source_id, organization_id=organization_id
        )

        result = await self.session.execute(
            select(GitHubConnection).where(
                GitHubConnection.knowledge_source_id == knowledge_source_id
            )
        )
        return result.scalar_one_or_none()

    async def connect(
        self,
        knowledge_source_id: uuid.UUID,
        *,
        organization_id: uuid.UUID | None,
        repository_owner: str,
        repository_name: str,
        token: str,
    ) -> GitHubConnection:
        await self.knowledge_sources.get_knowledge_source(
            knowledge_source_id, organization_id=organization_id
        )

        existing = await self.session.execute(
            select(GitHubConnection).where(
                GitHubConnection.knowledge_source_id == knowledge_source_id
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise GitHubConnectionAlreadyExistsError(
                "This knowledge source already has a GitHub connection."
            )

        # Validate the token and repository before persisting any credentials.
        repository = await validate_repository_access(
            token, repository_owner, repository_name
        )

        connection = GitHubConnection(
            knowledge_source_id=knowledge_source_id,
            repository_owner=repository.owner,
            repository_name=repository.name,
            encrypted_token=encrypt_credential(token),
            sync_status="pending",
        )
        self.session.add(connection)

        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise GitHubConnectionAlreadyExistsError(
                "This knowledge source already has a GitHub connection."
            ) from exc

        await self.session.refresh(connection)
        return connection

    async def disconnect(
        self,
        knowledge_source_id: uuid.UUID,
        *,
        organization_id: uuid.UUID | None,
    ) -> bool:
        connection = await self.get_connection(
            knowledge_source_id, organization_id=organization_id
        )
        if connection is None:
            return False

        await self.session.delete(connection)
        await self.session.commit()
        return True
