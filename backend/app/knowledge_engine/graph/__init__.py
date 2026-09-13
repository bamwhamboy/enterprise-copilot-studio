"""Graph RAG extraction and persistence.

This package builds a per-document knowledge graph (entities +
relationships, with provenance) from the same HierarchicalChunk
objects the existing vector pipeline already produces. It is
deliberately independent of that pipeline: nothing here reads from or
writes to Qdrant, and nothing in the vector/BM25 retrieval path
depends on this package. See ``graph_extraction_service.py`` for the
orchestration entry point.
"""
