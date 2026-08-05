"""Qdrant vector store wiring.

Builds a ``QdrantClient`` + LlamaIndex ``QdrantVectorStore`` bound to
``settings.QDRANT_COLLECTION_NAME``. The collection ("knowledge_chunks"
by default) is created automatically by ``QdrantVectorStore`` on first
insert if it doesn't already exist, sized to match the embedding
model's output dimension.
"""

from __future__ import annotations

from qdrant_client import QdrantClient
from llama_index.vector_stores.qdrant import QdrantVectorStore

from app.core.config import Settings


def build_qdrant_client(settings: Settings) -> QdrantClient:
    """Build a QdrantClient from ``settings.QDRANT_URL``."""
    return QdrantClient(url=settings.QDRANT_URL)


def build_vector_store(settings: Settings, client: QdrantClient) -> QdrantVectorStore:
    """Build a QdrantVectorStore bound to the configured collection."""
    return QdrantVectorStore(client=client, collection_name=settings.QDRANT_COLLECTION_NAME)
