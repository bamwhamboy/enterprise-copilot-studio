"""Indexing endpoint: chunk -> embed -> store -> mark a document indexed."""

import uuid

from fastapi import APIRouter, status

from app.core.dependencies import IndexingServiceDep
from app.schemas.search import IndexDocumentResponse

router = APIRouter(prefix="/index", tags=["Indexing"])


@router.post(
    "/{document_id}",
    response_model=IndexDocumentResponse,
    status_code=status.HTTP_200_OK,
    summary="Index a parsed document into the vector store",
)
async def index_document(
    document_id: uuid.UUID, service: IndexingServiceDep
) -> IndexDocumentResponse:
    result = await service.index_document(document_id)
    return IndexDocumentResponse(
        document_id=document_id,
        chunks_indexed=result["chunks_indexed"],
        index_status="INDEXED",
    )
