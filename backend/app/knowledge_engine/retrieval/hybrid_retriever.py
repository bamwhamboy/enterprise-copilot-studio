"""Hybrid retrieval.

Combines semantic (dense vector, via Qdrant) and BM25 (sparse,
term-frequency) retrieval, fused with Reciprocal Rank Fusion (RRF).
Supports metadata filtering by ``knowledge_source_id``.
"""

from __future__ import annotations

from qdrant_client import QdrantClient
from qdrant_client.http.models import FieldCondition, Filter, MatchValue
from llama_index.core import StorageContext, VectorStoreIndex
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.schema import NodeWithScore, TextNode
from llama_index.core.vector_stores.utils import metadata_dict_to_node
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.vector_stores.qdrant import QdrantVectorStore

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)

RRF_K = 60


def reciprocal_rank_fusion(
    result_lists: list[list[NodeWithScore]], k: int = RRF_K
) -> list[NodeWithScore]:
    """Combine multiple ranked result lists into one, via RRF.

    Each node's fused score is the sum, over every list it appears in,
    of ``1 / (k + rank)`` — ``rank`` being its 1-indexed position in
    that list. Standard, retriever-agnostic hybrid ranking: it needs
    only rank order from each retriever, not comparable raw scores.
    """
    fused_scores: dict[str, float] = {}
    node_lookup: dict[str, NodeWithScore] = {}

    for results in result_lists:
        for rank, node_with_score in enumerate(results, start=1):
            node_id = node_with_score.node.node_id
            fused_scores[node_id] = fused_scores.get(node_id, 0.0) + 1.0 / (k + rank)
            node_lookup[node_id] = node_with_score

    ranked_ids = sorted(fused_scores, key=lambda nid: fused_scores[nid], reverse=True)
    return [
        NodeWithScore(node=node_lookup[node_id].node, score=fused_scores[node_id])
        for node_id in ranked_ids
    ]


class HybridRetriever:
    """Combines semantic + BM25 retrieval over the knowledge_chunks collection, via RRF."""

    def __init__(
        self,
        settings: Settings,
        client: QdrantClient,
        vector_store: QdrantVectorStore,
        embed_model: BaseEmbedding,
    ) -> None:
        self._settings = settings
        self._client = client
        self._vector_store = vector_store
        self._embed_model = embed_model

    def _build_qdrant_filter(self, knowledge_source_id: str | None) -> Filter | None:
        if not knowledge_source_id:
            return None
        return Filter(
            must=[
                FieldCondition(
                    key="knowledge_source_id", match=MatchValue(value=knowledge_source_id)
                )
            ]
        )

    def _fetch_corpus_nodes(
        self, *, knowledge_source_id: str | None, limit: int = 1000
    ) -> list[TextNode]:
        """Scroll matching chunks from Qdrant to build a BM25 corpus.

        Rebuilding BM25's corpus from Qdrant on every search is a
        deliberate simplification at this sprint's scale — production
        would maintain a persisted, incrementally-updated BM25 index
        instead of reconstructing it per request.
        """
        query_filter = self._build_qdrant_filter(knowledge_source_id)
        points, _ = self._client.scroll(
            collection_name=self._settings.QDRANT_COLLECTION_NAME,
            scroll_filter=query_filter,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )
        nodes: list[TextNode] = []
        for point in points:
            if not point.payload:
                continue
            node = metadata_dict_to_node(point.payload)
            if isinstance(node, TextNode):
                nodes.append(node)
        return nodes

    @staticmethod
    def _to_llama_filters(knowledge_source_id: str | None):
        if not knowledge_source_id:
            return None
        from llama_index.core.vector_stores.types import ExactMatchFilter, MetadataFilters

        return MetadataFilters(
            filters=[ExactMatchFilter(key="knowledge_source_id", value=knowledge_source_id)]
        )

    def retrieve(
        self,
        query: str,
        *,
        knowledge_source_id: str | None = None,
        semantic_top_k: int | None = None,
        bm25_top_k: int | None = None,
        final_top_k: int | None = None,
    ) -> list[NodeWithScore]:
        """Run semantic + BM25 retrieval and fuse the results via RRF."""
        if not self._client.collection_exists(self._settings.QDRANT_COLLECTION_NAME):
            logger.info("Search for %r found no collection yet — nothing indexed.", query)
            return []

        semantic_top_k = semantic_top_k or self._settings.HYBRID_SEMANTIC_TOP_K
        bm25_top_k = bm25_top_k or self._settings.HYBRID_BM25_TOP_K
        final_top_k = final_top_k or self._settings.HYBRID_FINAL_TOP_K

        # --- Semantic retrieval ---
        storage_context = StorageContext.from_defaults(vector_store=self._vector_store)
        index = VectorStoreIndex(
            [], storage_context=storage_context, embed_model=self._embed_model
        )
        semantic_retriever = index.as_retriever(
            similarity_top_k=semantic_top_k,
            filters=self._to_llama_filters(knowledge_source_id),
        )
        semantic_results = semantic_retriever.retrieve(query)

        # --- BM25 retrieval ---
        corpus_nodes = self._fetch_corpus_nodes(knowledge_source_id=knowledge_source_id)
        bm25_results: list[NodeWithScore] = []
        if corpus_nodes:
            bm25_retriever = BM25Retriever.from_defaults(
                nodes=corpus_nodes, similarity_top_k=min(bm25_top_k, len(corpus_nodes))
            )
            bm25_results = bm25_retriever.retrieve(query)

        logger.info(
            "Hybrid retrieval for %r: %d semantic + %d BM25 candidates",
            query,
            len(semantic_results),
            len(bm25_results),
        )

        fused = reciprocal_rank_fusion([semantic_results, bm25_results])
        return fused[:final_top_k]
