"""Chunk listing endpoint — reads directly from Qdrant, the single source
of truth for chunk-level content and metadata (Postgres tracks document-
level status only).
"""

import uuid

from fastapi import APIRouter
from qdrant_client.http.models import FieldCondition, Filter, MatchValue
from llama_index.core.vector_stores.utils import metadata_dict_to_node

from app.core.dependencies import QdrantClientDep, SettingsDep
from app.schemas.chunk import ChunkListResponse, ChunkRead

router = APIRouter(prefix="/chunks", tags=["Chunks"])


@router.get(
    "/{document_id}",
    response_model=ChunkListResponse,
    summary="List all indexed chunks for a document",
)
async def list_chunks(
    document_id: uuid.UUID,
    client: QdrantClientDep,
    settings: SettingsDep,
) -> ChunkListResponse:
    if not client.collection_exists(settings.QDRANT_COLLECTION_NAME):
        return ChunkListResponse(document_id=str(document_id), chunks=[])

    query_filter = Filter(
        must=[FieldCondition(key="source_document_id", match=MatchValue(value=str(document_id)))]
    )

    points, _ = client.scroll(
        collection_name=settings.QDRANT_COLLECTION_NAME,
        scroll_filter=query_filter,
        limit=1000,
        with_payload=True,
        with_vectors=False,
    )

    chunks: list[ChunkRead] = []
    for point in points:
        payload = point.payload or {}
        node = metadata_dict_to_node(payload)
        chunks.append(
            ChunkRead(
                chunk_id=str(point.id),
                text=node.get_content(),
                document_id=payload.get("source_document_id", ""),
                knowledge_source_id=payload.get("knowledge_source_id", ""),
                document_name=payload.get("document_name", ""),
                chunk_number=payload.get("chunk_number", 0),
                page_number=payload.get("page_number"),
                section=payload.get("section"),
                subsection=payload.get("subsection"),
            )
        )

    chunks.sort(key=lambda c: c.chunk_number)
    return ChunkListResponse(document_id=str(document_id), chunks=chunks)
