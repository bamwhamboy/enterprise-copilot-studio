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
    # Bug fix: previously this field didn't exist at all, so a graph
    # extraction failure (partial or total) was completely invisible
    # from the API response -- indistinguishable from full success.
    # None only when graph extraction is disabled entirely (see
    # IndexingService._run_graph_extraction's {"status": "skipped"}).
    graph_extraction: dict | None = None
