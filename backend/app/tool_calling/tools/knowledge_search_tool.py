"""Knowledge Search tool.

Wraps the existing Hybrid Hierarchical RAG retrieval (Sprint 3B) plus
context compression as a single callable tool, so the chat runtime's
retrieval node -- and any future agent -- can invoke it uniformly
through the tool-calling framework rather than importing the retriever
directly.
"""

from __future__ import annotations

from app.knowledge_engine.citations.citation_builder import build_retrieved_chunks
from app.knowledge_engine.compression.compression_service import ContextCompressionService
from app.knowledge_engine.retrieval.hybrid_retriever import HybridRetriever
from app.tool_calling.base import Tool, ToolResult


class KnowledgeSearchTool(Tool):
    name = "knowledge_search"
    description = (
        "Search the enterprise knowledge base for information relevant to a "
        "question. Returns ranked, cited text chunks. Use this before "
        "answering any question that may depend on organization-specific "
        "policies or documents."
    )

    def __init__(self, retriever: HybridRetriever, compression: ContextCompressionService) -> None:
        self._retriever = retriever
        self._compression = compression

    async def execute(
        self, *, query: str, knowledge_source_id: str | None = None, top_k: int | None = None
    ) -> ToolResult:
        node_results = self._retriever.retrieve(
            query, knowledge_source_id=knowledge_source_id, final_top_k=top_k
        )
        retrieved = build_retrieved_chunks(node_results)
        compressed = self._compression.compress(retrieved)

        return ToolResult(
            tool_name=self.name,
            success=True,
            output=[chunk.model_dump(mode="json") for chunk in compressed],
        )
