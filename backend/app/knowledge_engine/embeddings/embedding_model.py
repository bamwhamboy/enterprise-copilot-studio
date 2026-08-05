"""Embedding model factory.

Builds a LlamaIndex ``BaseEmbedding`` for ``BAAI/bge-small-en-v1.5`` via
``HuggingFaceEmbedding``. Downloading the model weights requires network
access to huggingface.co — where that's unavailable (this sandbox
included, and any CI environment without external network), inject
``llama_index.core.embeddings.MockEmbedding`` instead. Both implement
the same ``BaseEmbedding`` interface, so nothing downstream (indexing,
retrieval) needs to know or care which one it got.
"""

from __future__ import annotations

from llama_index.core.base.embeddings.base import BaseEmbedding

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def build_embedding_model(settings: Settings) -> BaseEmbedding:
    """Build the real HuggingFace embedding model for production use.

    Downloads ``settings.EMBEDDING_MODEL_NAME`` on first use — requires
    network access to huggingface.co.
    """
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding

    logger.info("Loading embedding model: %s", settings.EMBEDDING_MODEL_NAME)
    return HuggingFaceEmbedding(model_name=settings.EMBEDDING_MODEL_NAME)
