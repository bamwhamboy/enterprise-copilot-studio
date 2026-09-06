"""V2 Smart Copilot Creation endpoints."""

import uuid

from fastapi import APIRouter

from app.core.dependencies import DocumentServiceDep, DocumentStorageServiceDep
from app.core.logging import get_logger
from app.schemas.document_classification import (
    DocumentClassificationRequest,
    DocumentClassificationResponse,
)
from app.security.dependencies import CurrentUser, scoped_organization_id
from app.services.document_intelligence_service import DocumentIntelligenceService

logger = get_logger(__name__)

router = APIRouter(prefix="/document-intelligence", tags=["V2 Document Intelligence"])


@router.post(
    "/classify",
    response_model=DocumentClassificationResponse,
    summary="Recommend a Copilot for a document",
)
async def classify_document(
    payload: DocumentClassificationRequest,
    user: CurrentUser,
) -> DocumentClassificationResponse:
    """Classify document signals and recommend the best Copilot domain.

    The authenticated user is intentionally required even though the first
    classifier is stateless. This keeps the V2 endpoint behind the same
    tenant boundary as the rest of the platform and gives us a safe seam
    for tenant-specific policies later.
    """
    _ = user
    return DocumentIntelligenceService().classify(payload)


@router.post(
    "/classify-document/{document_id}",
    response_model=DocumentClassificationResponse,
    summary="Recommend a Copilot for an already-uploaded document",
)
async def classify_uploaded_document(
    document_id: uuid.UUID,
    user: CurrentUser,
    documents: DocumentServiceDep,
    storage: DocumentStorageServiceDep,
) -> DocumentClassificationResponse:
    """Classify an already-uploaded document using its extracted text.

    The document lookup is org-scoped through the existing DocumentService.
    The ingestion pipeline already stores extracted text as a sidecar file,
    so this route reads that content through the existing storage boundary
    and feeds it into the same deterministic classifier used by /classify.

    If extraction did not produce a sidecar path, classification gracefully
    falls back to filename-only signals. The extracted content is truncated
    to the classifier contract's 50,000-character maximum.
    """
    document = await documents.get_document(
        document_id, organization_id=scoped_organization_id(user)
    )

    text = ""
    if document.extracted_text_path:
        try:
            text = (await storage.load_bytes(document.extracted_text_path)).decode("utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            logger.warning(
                "Could not read extracted text for document %s at %s (%s); "
                "falling back to filename-only classification.",
                document.id,
                document.extracted_text_path,
                exc,
            )

    payload = DocumentClassificationRequest(
        filename=document.original_filename or document.name,
        text=text[:50_000],
    )
    return DocumentIntelligenceService().classify(payload)
