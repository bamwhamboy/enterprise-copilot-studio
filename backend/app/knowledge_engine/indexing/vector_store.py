"""Qdrant vector store wiring.

Builds a ``QdrantClient`` + LlamaIndex ``QdrantVectorStore`` bound to
``settings.QDRANT_COLLECTION_NAME``, and ensures the collection is
fully initialized -- created if missing, with a payload index on every
field the app actually filters by.
"""

from __future__ import annotations

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, PayloadSchemaType, VectorParams
from llama_index.vector_stores.qdrant import QdrantVectorStore

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Every field the app filters Qdrant results by. Qdrant Cloud requires a
# payload index to exist before a field can be used in a filter at all
# ("Bad request: Index required but not found for ..."); local/in-memory
# Qdrant (this project's own test suite) is more permissive and allows
# unindexed filtering, which is exactly why this went unnoticed until a
# real Qdrant Cloud deployment. Confirmed by grepping every filter
# construction in the codebase (MatchValue/FieldCondition/
# ExactMatchFilter usages) rather than assumed:
#   - "knowledge_source_id": app/knowledge_engine/retrieval/hybrid_retriever.py
#     (both the semantic-search filter and the BM25 corpus scroll filter)
#   - "source_document_id": app/api/v1/chunks.py (GET /chunks/{document_id})
_FILTERED_PAYLOAD_FIELDS: dict[str, PayloadSchemaType] = {
    "knowledge_source_id": PayloadSchemaType.KEYWORD,
    "source_document_id": PayloadSchemaType.KEYWORD,
}


def build_qdrant_client(settings: Settings) -> QdrantClient:
    """Build a QdrantClient from ``settings.QDRANT_URL``.

    Passes ``settings.QDRANT_API_KEY`` when set -- required for any
    authenticated Qdrant instance (Qdrant Cloud in particular always
    requires one). This was previously a real, silent bug: the
    settings field existed and could be set, but was never actually
    passed to the client, so setting QDRANT_API_KEY had no effect at
    all -- the client would still connect unauthenticated and Qdrant
    Cloud would reject the request.
    """
    return QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)


def ensure_collection_ready(client: QdrantClient, settings: Settings) -> None:
    """Ensure the collection exists and has every required payload index.

    Idempotent and safe to call on every application startup, whether
    the collection is brand new or has existed (without these indexes)
    since before this fix:
      - If the collection doesn't exist yet, it's created explicitly
        here (matching what LlamaIndex's QdrantVectorStore would have
        created lazily on first insert -- same vector size and
        distance metric, so this doesn't change what gets created,
        only makes it happen deterministically up front instead of on
        whatever request happens to insert first).
      - create_payload_index is called for every field in
        _FILTERED_PAYLOAD_FIELDS regardless of whether the collection
        was just created or already existed. Verified directly against
        a real QdrantClient: calling it a second time with the same
        field name/schema does not raise -- it returns the same
        "completed" status both times, which is exactly what makes
        this safe to run unconditionally on every startup rather than
        needing its own "did I already do this" bookkeeping.
    """
    if not client.collection_exists(settings.QDRANT_COLLECTION_NAME):
        logger.info(
            "Creating Qdrant collection %s (size=%d, distance=cosine)",
            settings.QDRANT_COLLECTION_NAME,
            settings.EMBEDDING_DIMENSION,
        )
        client.create_collection(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            vectors_config=VectorParams(
                size=settings.EMBEDDING_DIMENSION,
                distance=Distance.COSINE,
            ),
        )

    for field_name, field_schema in _FILTERED_PAYLOAD_FIELDS.items():
        client.create_payload_index(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            field_name=field_name,
            field_schema=field_schema,
        )
    logger.info(
        "Qdrant collection %s ready (payload indexes: %s)",
        settings.QDRANT_COLLECTION_NAME,
        ", ".join(_FILTERED_PAYLOAD_FIELDS),
    )


def build_vector_store(settings: Settings, client: QdrantClient) -> QdrantVectorStore:
    """Build a QdrantVectorStore bound to the configured collection."""
    return QdrantVectorStore(client=client, collection_name=settings.QDRANT_COLLECTION_NAME)
