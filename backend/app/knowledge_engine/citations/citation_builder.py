"""Citation builder.

Converts a retrieved LlamaIndex ``NodeWithScore`` into this codebase's
own ``Citation``/``RetrievedChunk`` shapes — keeping every consumer
(compression, the search API, the future HR Copilot) decoupled from
LlamaIndex's node types.
"""

from __future__ import annotations

from llama_index.core.schema import NodeWithScore

from app.knowledge_engine.models import Citation, RetrievedChunk


def build_citation(node_with_score: NodeWithScore) -> Citation:
    metadata = node_with_score.node.metadata or {}
    return Citation(
        # "source_document_id" (not "document_id") is the payload key
        # actually written at index time -- see indexing_service.py's
        # _chunk_to_node, which renames it specifically to dodge a
        # LlamaIndex collision with node.ref_doc_id. Defaults to "" (same
        # style as knowledge_source_id below) rather than fabricating an
        # id when metadata genuinely doesn't carry one.
        document_id=metadata.get("source_document_id", ""),
        document_name=metadata.get("document_name", "Unknown document"),
        knowledge_source_id=metadata.get("knowledge_source_id", ""),
        page_number=metadata.get("page_number"),
        section=metadata.get("section"),
        chunk_number=metadata.get("chunk_number", 0),
        score=node_with_score.score,
    )


def build_retrieved_chunk(node_with_score: NodeWithScore) -> RetrievedChunk:
    return RetrievedChunk(
        text=node_with_score.node.get_content(),
        score=node_with_score.score or 0.0,
        citation=build_citation(node_with_score),
        chunk_id=node_with_score.node.node_id,
    )


def build_retrieved_chunks(results: list[NodeWithScore]) -> list[RetrievedChunk]:
    return [build_retrieved_chunk(result) for result in results]
