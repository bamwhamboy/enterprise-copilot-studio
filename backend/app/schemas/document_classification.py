"""Contracts for V2 document intelligence and Copilot recommendations."""

from pydantic import BaseModel, Field


class DocumentClassificationRequest(BaseModel):
    """Minimal document signal used to recommend a Copilot."""

    filename: str = Field(min_length=1, max_length=512)
    text: str = Field(default="", max_length=50_000)


class DocumentClassificationResponse(BaseModel):
    """Domain/type prediction and the corresponding Copilot recommendation."""

    domain: str
    document_type: str
    confidence: float = Field(ge=0.0, le=1.0)
    recommended_copilot: str
    matched_signals: list[str] = Field(default_factory=list)
