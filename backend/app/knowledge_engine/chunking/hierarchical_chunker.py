"""Hierarchical chunking.

Wraps LlamaIndex's ``HierarchicalNodeParser`` to produce Document ->
Section -> Subsection -> Paragraph structured chunks, with parent-child
relationships preserved (LlamaIndex encodes this via
``NodeRelationship.PARENT``/``CHILD`` on each node).

Uses ``TokenTextSplitter`` (tiktoken-based) at every level instead of
the parser's default ``SentenceSplitter`` (NLTK-based, requires
downloading punkt tokenizer data at runtime) — this keeps chunking
fully offline, with no dependency on reaching an NLTK data server.
"""

from __future__ import annotations

from llama_index.core import Document as LlamaDocument
from llama_index.core.node_parser import HierarchicalNodeParser, TokenTextSplitter
from llama_index.core.schema import BaseNode, NodeRelationship

from app.core.config import Settings
from app.core.logging import get_logger
from app.knowledge_engine.models import ChunkMetadata, HierarchicalChunk

logger = get_logger(__name__)


def _build_parser(chunk_sizes: list[int], chunk_overlap: int = 20) -> HierarchicalNodeParser:
    node_parser_ids = [f"chunk_size_{size}" for size in chunk_sizes]
    node_parser_map = {
        node_id: TokenTextSplitter(chunk_size=size, chunk_overlap=chunk_overlap)
        for node_id, size in zip(node_parser_ids, chunk_sizes)
    }
    return HierarchicalNodeParser.from_defaults(
        node_parser_ids=node_parser_ids,
        node_parser_map=node_parser_map,
    )


class HierarchicalChunker:
    """Splits document text into a hierarchy of metadata-enriched chunks."""

    def __init__(self, settings: Settings) -> None:
        self._chunk_sizes = settings.CHUNK_SIZES
        self._parser = _build_parser(self._chunk_sizes)

    def chunk(
        self,
        *,
        text: str,
        document_id: str,
        knowledge_source_id: str,
        document_name: str,
    ) -> list[HierarchicalChunk]:
        """Split ``text`` into hierarchical chunks, each with required metadata attached."""
        llama_doc = LlamaDocument(text=text, doc_id=document_id)
        nodes: list[BaseNode] = self._parser.get_nodes_from_documents([llama_doc])

        chunks: list[HierarchicalChunk] = []
        for index, node in enumerate(nodes):
            parent_relationship = node.relationships.get(NodeRelationship.PARENT)
            parent_id = parent_relationship.node_id if parent_relationship else None

            metadata = ChunkMetadata(
                document_id=document_id,
                knowledge_source_id=knowledge_source_id,
                document_name=document_name,
                chunk_number=index,
                # section/subsection/page_number aren't derivable from plain
                # extracted text alone — no layout information survives
                # PDF -> text extraction. Left None here; a future,
                # layout-aware parser can populate them without changing
                # this shape or any downstream consumer.
            )
            chunks.append(
                HierarchicalChunk(
                    text=node.get_content(),
                    metadata=metadata,
                    parent_chunk_id=parent_id,
                    node_id=node.node_id,
                )
            )

        logger.info(
            "Chunked document %s into %d hierarchical nodes (chunk_sizes=%s)",
            document_id,
            len(chunks),
            self._chunk_sizes,
        )
        return chunks
