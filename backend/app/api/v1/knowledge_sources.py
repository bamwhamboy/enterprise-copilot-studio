"""KnowledgeSource CRUD endpoints."""

import uuid

from fastapi import APIRouter, Query, status

from app.core.dependencies import KnowledgeSourceServiceDep
from app.schemas.knowledge_source import (
    KnowledgeSourceCreate,
    KnowledgeSourceRead,
    KnowledgeSourceUpdate,
)

router = APIRouter(prefix="/knowledge-sources", tags=["Knowledge Sources"])


@router.get("", response_model=list[KnowledgeSourceRead], summary="List knowledge sources")
async def list_knowledge_sources(
    service: KnowledgeSourceServiceDep,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[KnowledgeSourceRead]:
    knowledge_sources = await service.list_knowledge_sources(offset=offset, limit=limit)
    return [KnowledgeSourceRead.model_validate(ks) for ks in knowledge_sources]


@router.get(
    "/{knowledge_source_id}",
    response_model=KnowledgeSourceRead,
    summary="Get a knowledge source",
)
async def get_knowledge_source(
    knowledge_source_id: uuid.UUID, service: KnowledgeSourceServiceDep
) -> KnowledgeSourceRead:
    knowledge_source = await service.get_knowledge_source(knowledge_source_id)
    return KnowledgeSourceRead.model_validate(knowledge_source)


@router.post(
    "",
    response_model=KnowledgeSourceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a knowledge source",
)
async def create_knowledge_source(
    payload: KnowledgeSourceCreate, service: KnowledgeSourceServiceDep
) -> KnowledgeSourceRead:
    knowledge_source = await service.create_knowledge_source(payload)
    return KnowledgeSourceRead.model_validate(knowledge_source)


@router.put(
    "/{knowledge_source_id}",
    response_model=KnowledgeSourceRead,
    summary="Update a knowledge source",
)
async def update_knowledge_source(
    knowledge_source_id: uuid.UUID,
    payload: KnowledgeSourceUpdate,
    service: KnowledgeSourceServiceDep,
) -> KnowledgeSourceRead:
    knowledge_source = await service.update_knowledge_source(knowledge_source_id, payload)
    return KnowledgeSourceRead.model_validate(knowledge_source)


@router.delete(
    "/{knowledge_source_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a knowledge source",
)
async def delete_knowledge_source(
    knowledge_source_id: uuid.UUID, service: KnowledgeSourceServiceDep
) -> None:
    await service.delete_knowledge_source(knowledge_source_id)
