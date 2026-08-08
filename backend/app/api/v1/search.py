"""Search endpoint: hybrid retrieval, context compression, and citations.

Tenant isolation follow-up: previously unauthenticated and unscoped,
searching across every organization's indexed content regardless of
who asked. Now requires authentication and constrains results to the
caller's own organization -- either to one specific, ownership-checked
knowledge source, or (when none is specified) to the full set of
knowledge sources the caller's organization actually owns, resolved
from Postgres via the same org-scoped KnowledgeSourceService used by
the CRUD endpoints, rather than searching globally.
"""

import uuid

from fastapi import APIRouter, Query

from app.core.dependencies import CompressionServiceDep, HybridRetrieverDep, KnowledgeSourceServiceDep
from app.knowledge_engine.citations.citation_builder import build_retrieved_chunks
from app.schemas.search import CitationRead, SearchResponse, SearchResultItem
from app.security.dependencies import CurrentUser, scoped_organization_id

router = APIRouter(tags=["Search"])


@router.get("/search", response_model=SearchResponse, summary="Hybrid search over indexed chunks")
async def search(
    user: CurrentUser,
    retriever: HybridRetrieverDep,
    compression: CompressionServiceDep,
    knowledge_source_service: KnowledgeSourceServiceDep,
    q: str = Query(..., min_length=1, description="Search query"),
    knowledge_source_id: uuid.UUID | None = Query(default=None),
    top_k: int | None = Query(default=None, ge=1, le=50),
) -> SearchResponse:
    organization_id = scoped_organization_id(user)

    knowledge_source_ids: list[str] | None = None
    resolved_single_id: str | None = None

    if knowledge_source_id:
        # Ownership check, reusing the same tested logic the CRUD
        # endpoint itself uses (404, not silently-empty, for a source
        # belonging to a different organization) -- this is what makes
        # an explicitly-requested knowledge_source_id safe to use as a
        # single-source filter below.
        await knowledge_source_service.get_knowledge_source(
            knowledge_source_id, organization_id=organization_id
        )
        resolved_single_id = str(knowledge_source_id)
    elif organization_id is not None:
        # No specific source requested -- constrain to every knowledge
        # source the caller's organization actually owns, rather than
        # searching globally across every organization's content.
        # super_admin (organization_id is None) intentionally stays
        # unrestricted here, matching its existing "see everything"
        # behavior elsewhere (e.g. GET /organizations).
        owned_sources = await knowledge_source_service.list_knowledge_sources(
            organization_id=organization_id, limit=10_000
        )
        knowledge_source_ids = [str(ks.id) for ks in owned_sources]
        if not knowledge_source_ids:
            # This organization owns no knowledge sources at all -- return
            # empty immediately rather than passing an empty filter list to
            # the retriever, which would be indistinguishable from "no
            # filter" (unrestricted) there.
            return SearchResponse(query=q, results=[])

    node_results = retriever.retrieve(
        q,
        knowledge_source_id=resolved_single_id,
        knowledge_source_ids=knowledge_source_ids,
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
