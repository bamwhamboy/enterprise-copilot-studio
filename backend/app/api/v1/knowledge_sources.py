"""KnowledgeSource CRUD endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.core.dependencies import DocumentServiceDep, IndexingServiceDep
from app.services.github_sync_service import GitHubSyncService, GitHubSyncError
from app.services.github_connection_service import (
    GitHubConnectionService,
    GitHubConnectionAlreadyExistsError,
)
from app.connectors.github_client import GitHubAPIError
from app.schemas.github_connection import (
    GitHubConnectionCreate,
    GitHubConnectionRead,
)

from app.core.dependencies import KnowledgeSourceServiceDep
from app.schemas.knowledge_source import (
    KnowledgeSourceCreate,
    KnowledgeSourceRead,
    KnowledgeSourceUpdate,
)
from app.security.dependencies import CurrentUser, scoped_organization_id

router = APIRouter(prefix="/knowledge-sources", tags=["Knowledge Sources"])


@router.get("", response_model=list[KnowledgeSourceRead], summary="List knowledge sources")
async def list_knowledge_sources(
    user: CurrentUser,
    service: KnowledgeSourceServiceDep,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[KnowledgeSourceRead]:
    knowledge_sources = await service.list_knowledge_sources(
        offset=offset, limit=limit, organization_id=scoped_organization_id(user)
    )
    return [KnowledgeSourceRead.model_validate(ks) for ks in knowledge_sources]


@router.get(
    "/{knowledge_source_id}",
    response_model=KnowledgeSourceRead,
    summary="Get a knowledge source",
)
async def get_knowledge_source(
    knowledge_source_id: uuid.UUID, user: CurrentUser, service: KnowledgeSourceServiceDep
) -> KnowledgeSourceRead:
    knowledge_source = await service.get_knowledge_source(
        knowledge_source_id, organization_id=scoped_organization_id(user)
    )
    return KnowledgeSourceRead.model_validate(knowledge_source)


@router.post(
    "",
    response_model=KnowledgeSourceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a knowledge source",
)
async def create_knowledge_source(
    payload: KnowledgeSourceCreate, user: CurrentUser, service: KnowledgeSourceServiceDep
) -> KnowledgeSourceRead:
    knowledge_source = await service.create_knowledge_source(
        payload, organization_id=user.organization_id
    )
    return KnowledgeSourceRead.model_validate(knowledge_source)


@router.put(
    "/{knowledge_source_id}",
    response_model=KnowledgeSourceRead,
    summary="Update a knowledge source",
)
async def update_knowledge_source(
    knowledge_source_id: uuid.UUID,
    payload: KnowledgeSourceUpdate,
    user: CurrentUser,
    service: KnowledgeSourceServiceDep,
) -> KnowledgeSourceRead:
    knowledge_source = await service.update_knowledge_source(
        knowledge_source_id, payload, organization_id=scoped_organization_id(user)
    )
    return KnowledgeSourceRead.model_validate(knowledge_source)


@router.delete(
    "/{knowledge_source_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a knowledge source",
)
async def delete_knowledge_source(
    knowledge_source_id: uuid.UUID, user: CurrentUser, service: KnowledgeSourceServiceDep
) -> None:
    await service.delete_knowledge_source(
        knowledge_source_id, organization_id=scoped_organization_id(user)
    )



@router.post(
    "/{knowledge_source_id}/github",
    response_model=GitHubConnectionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Connect a GitHub repository",
)
async def connect_github_repository(
    knowledge_source_id: uuid.UUID,
    payload: GitHubConnectionCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_db),
) -> GitHubConnectionRead:
    service = GitHubConnectionService(session)
    try:
        connection = await service.connect(
            knowledge_source_id,
            organization_id=scoped_organization_id(user),
            repository_owner=payload.repository_owner,
            repository_name=payload.repository_name,
            token=payload.token,
        )
    except GitHubConnectionAlreadyExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except GitHubAPIError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail="GitHub credential encryption is not configured.",
        ) from exc

    return GitHubConnectionRead.model_validate(connection)


@router.get(
    "/{knowledge_source_id}/github",
    response_model=GitHubConnectionRead,
    summary="Get GitHub connection status",
)
async def get_github_connection(
    knowledge_source_id: uuid.UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_db),
) -> GitHubConnectionRead:
    service = GitHubConnectionService(session)
    connection = await service.get_connection(
        knowledge_source_id,
        organization_id=scoped_organization_id(user),
    )
    if connection is None:
        raise HTTPException(status_code=404, detail="GitHub connection not found.")
    return GitHubConnectionRead.model_validate(connection)


@router.delete(
    "/{knowledge_source_id}/github",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Disconnect GitHub repository",
)
async def disconnect_github_repository(
    knowledge_source_id: uuid.UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_db),
) -> None:
    service = GitHubConnectionService(session)
    await service.disconnect(
        knowledge_source_id,
        organization_id=scoped_organization_id(user),
    )



@router.post(
    "/{knowledge_source_id}/github/sync",
    summary="Synchronize GitHub repository into the knowledge base",
)
async def sync_github_repository(
    knowledge_source_id: uuid.UUID,
    user: CurrentUser,
    document_service: DocumentServiceDep,
    indexing_service: IndexingServiceDep,
    session: AsyncSession = Depends(get_db),
) -> dict:
    service = GitHubSyncService(
        session=session,
        document_service=document_service,
        indexing_service=indexing_service,
    )
    try:
        return await service.sync(
            knowledge_source_id,
            organization_id=scoped_organization_id(user),
        )
    except GitHubSyncError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except GitHubAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=503,
            detail="GitHub credentials could not be decrypted.",
        ) from exc
