"""Enterprise Knowledge Engine.

Sprint 3A implements the **ingestion** side: accepting uploaded PDFs,
storing them, extracting text/metadata via PyMuPDF, and registering
documents in PostgreSQL — under ``storage/``, ``parser/``, ``metadata/``,
and ``pipeline/``.

Retrieval proper (Hierarchical Hybrid RAG: dense + BM25 hybrid search,
re-ranking, context compression/summarization, citation generation,
built on LlamaIndex and Qdrant) is **not yet implemented** — that's a
later sprint building on top of the documents this one registers.
"""
