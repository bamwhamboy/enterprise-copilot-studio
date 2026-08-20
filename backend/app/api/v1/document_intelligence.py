"""V2 Smart Copilot Creation endpoints."""

from fastapi import APIRouter

from app.schemas.document_classification import (
    DocumentClassificationRequest,
    DocumentClassificationResponse,
)
from app.security.dependencies import CurrentUser
from app.services.document_intelligence_service import DocumentIntelligenceService

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
