"""Copilot CRUD endpoints."""

import uuid

from fastapi import APIRouter, Query, status

from app.core.dependencies import CopilotServiceDep
from app.schemas.copilot import CopilotCreate, CopilotRead, CopilotUpdate

router = APIRouter(prefix="/copilots", tags=["Copilots"])


@router.get("", response_model=list[CopilotRead], summary="List copilots")
async def list_copilots(
    service: CopilotServiceDep,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[CopilotRead]:
    copilots = await service.list_copilots(offset=offset, limit=limit)
    return [CopilotRead.model_validate(c) for c in copilots]


@router.get("/{copilot_id}", response_model=CopilotRead, summary="Get a copilot")
async def get_copilot(copilot_id: uuid.UUID, service: CopilotServiceDep) -> CopilotRead:
    copilot = await service.get_copilot(copilot_id)
    return CopilotRead.model_validate(copilot)


@router.post(
    "",
    response_model=CopilotRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a copilot",
)
async def create_copilot(payload: CopilotCreate, service: CopilotServiceDep) -> CopilotRead:
    copilot = await service.create_copilot(payload)
    return CopilotRead.model_validate(copilot)


@router.put("/{copilot_id}", response_model=CopilotRead, summary="Update a copilot")
async def update_copilot(
    copilot_id: uuid.UUID, payload: CopilotUpdate, service: CopilotServiceDep
) -> CopilotRead:
    copilot = await service.update_copilot(copilot_id, payload)
    return CopilotRead.model_validate(copilot)


@router.delete(
    "/{copilot_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a copilot",
)
async def delete_copilot(copilot_id: uuid.UUID, service: CopilotServiceDep) -> None:
    await service.delete_copilot(copilot_id)
