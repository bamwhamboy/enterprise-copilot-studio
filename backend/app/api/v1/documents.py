"""Document endpoints — GET, POST, DELETE only (no update endpoint, per spec)."""

import uuid

from fastapi import APIRouter, Query, status

from app.core.dependencies import DocumentServiceDep
from app.schemas.document import DocumentCreate, DocumentRead

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.get("", response_model=list[DocumentRead], summary="List documents")
async def list_documents(
    service: DocumentServiceDep,
    knowledge_source_id: uuid.UUID | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[DocumentRead]:
    documents = await service.list_documents(
        offset=offset, limit=limit, knowledge_source_id=knowledge_source_id
    )
    return [DocumentRead.model_validate(d) for d in documents]


@router.get("/{document_id}", response_model=DocumentRead, summary="Get a document")
async def get_document(document_id: uuid.UUID, service: DocumentServiceDep) -> DocumentRead:
    document = await service.get_document(document_id)
    return DocumentRead.model_validate(document)


@router.post(
    "",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a document",
)
async def create_document(payload: DocumentCreate, service: DocumentServiceDep) -> DocumentRead:
    document = await service.create_document(payload)
    return DocumentRead.model_validate(document)


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document",
)
async def delete_document(document_id: uuid.UUID, service: DocumentServiceDep) -> None:
    await service.delete_document(document_id)
