"""Search endpoint: hybrid retrieval, context compression, and citations."""

import uuid

from fastapi import APIRouter, Query

from app.core.dependencies import CompressionServiceDep, HybridRetrieverDep
from app.knowledge_engine.citations.citation_builder import build_retrieved_chunks
from app.schemas.search import CitationRead, SearchResponse, SearchResultItem

router = APIRouter(tags=["Search"])


@router.get("/search", response_model=SearchResponse, summary="Hybrid search over indexed chunks")
async def search(
    retriever: HybridRetrieverDep,
    compression: CompressionServiceDep,
    q: str = Query(..., min_length=1, description="Search query"),
    knowledge_source_id: uuid.UUID | None = Query(default=None),
    top_k: int | None = Query(default=None, ge=1, le=50),
) -> SearchResponse:
    node_results = retriever.retrieve(
        q,
        knowledge_source_id=str(knowledge_source_id) if knowledge_source_id else None,
        final_top_k=top_k,
    )
    retrieved_chunks = build_retrieved_chunks(node_results)
    compressed_chunks = compression.compress(retrieved_chunks)

    return SearchResponse(
        query=q,
        results=[
            SearchResultItem(
                text=chunk.text,
                score=chunk.score,
                chunk_id=chunk.chunk_id,
                citation=CitationRead(**chunk.citation.model_dump()),
            )
            for chunk in compressed_chunks
        ],
    )
