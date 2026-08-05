"""Schema for chunk listing."""

from pydantic import BaseModel, Field


class ChunkRead(BaseModel):
    chunk_id: str
    text: str
    document_id: str
    knowledge_source_id: str
    document_name: str
    chunk_number: int
    page_number: int | None = None
    section: str | None = None
    subsection: str | None = None


class ChunkListResponse(BaseModel):
    document_id: str
    chunks: list[ChunkRead] = Field(default_factory=list)
