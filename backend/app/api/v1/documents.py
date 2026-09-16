"""Document endpoints.

GET / POST / DELETE for the Sprint 2 JSON-based CRUD (unchanged), plus
the Sprint 3A ``POST /upload`` for real document ingestion. Supports
PDF, DOCX, TXT, PPTX, CSV, and XLSX (see
``app/knowledge_engine/parser/registry.py``). No PUT/update endpoint,
per spec.
"""

import uuid

from fastapi import APIRouter, File, Form, Query, UploadFile, status

from app.core.dependencies import DocumentServiceDep
from app.schemas.document import DocumentCreate, DocumentRead
from app.security.dependencies import CurrentUser, scoped_organization_id

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.get("", response_model=list[DocumentRead], summary="List documents")
async def list_documents(
    user: CurrentUser,
    service: DocumentServiceDep,
    knowledge_source_id: uuid.UUID | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[DocumentRead]:
    documents = await service.list_documents(
        offset=offset,
        limit=limit,
        knowledge_source_id=knowledge_source_id,
        organization_id=scoped_organization_id(user),
    )
    return [DocumentRead.model_validate(d) for d in documents]


@router.get("/{document_id}", response_model=DocumentRead, summary="Get a document")
async def get_document(
    document_id: uuid.UUID, user: CurrentUser, service: DocumentServiceDep
) -> DocumentRead:
    document = await service.get_document(
        document_id, organization_id=scoped_organization_id(user)
    )
    return DocumentRead.model_validate(document)


@router.post(
    "",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a document (JSON, no file)",
)
async def create_document(
    payload: DocumentCreate, user: CurrentUser, service: DocumentServiceDep
) -> DocumentRead:
    document = await service.create_document(
        payload, organization_id=scoped_organization_id(user)
    )
    return DocumentRead.model_validate(document)


@router.post(
    "/upload",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a document (PDF, DOCX, TXT, PPTX, CSV, or XLSX)",
)
async def upload_document(
    user: CurrentUser,
    service: DocumentServiceDep,
    knowledge_source_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
) -> DocumentRead:
    content = await file.read()
    document = await service.upload_document(
        knowledge_source_id=knowledge_source_id,
        # No extension here deliberately doesn't default to any one
        # supported format (previously this defaulted to ".pdf",
        # which would silently try to parse non-PDF bytes as a PDF
        # instead of failing validation cleanly) -- an extensionless
        # ".bin" filename always fails the registry's extension check
        # with a clean 415, regardless of which formats are supported.
        filename=file.filename or "upload.bin",
        content_type=file.content_type,
        content=content,
        organization_id=scoped_organization_id(user),
    )
    return DocumentRead.model_validate(document)


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document",
)
async def delete_document(
    document_id: uuid.UUID, user: CurrentUser, service: DocumentServiceDep
) -> None:
    await service.delete_document(document_id, organization_id=scoped_organization_id(user))
