"""Schemas for the search/retrieval API."""

import uuid

from pydantic import BaseModel, Field


class CitationRead(BaseModel):
    document_name: str
    knowledge_source_id: str
    page_number: int | None = None
    section: str | None = None
    chunk_number: int
    score: float | None = None


class SearchResultItem(BaseModel):
    text: str
    score: float
    chunk_id: str
    citation: CitationRead


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResultItem] = Field(default_factory=list)


class IndexDocumentResponse(BaseModel):
    document_id: uuid.UUID
    chunks_indexed: int
    index_status: str
