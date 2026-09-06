"""Tests for app.knowledge_engine.citations.citation_builder.

Pure unit tests -- no LLM, no database, no Qdrant, no network call.
Builds NodeWithScore objects directly (the exact type HybridRetriever.
retrieve() returns, and what build_citation()/build_retrieved_chunk()
actually consume) with realistic metadata dicts, matching the payload
shape indexing_service.py's _chunk_to_node() actually writes (including
the "source_document_id" rename -- see that module's own comment on
why "document_id" itself can't be used as the payload key).

Regression coverage for Fix #2A: build_citation() previously read every
other metadata field (document_name, knowledge_source_id, page_number,
section, chunk_number) but never source_document_id, so Citation.
document_id didn't exist and every retrieved chunk's true document
identity was silently dropped on the read path even though it was
already present in Qdrant's payload.
"""

from __future__ import annotations

from llama_index.core.schema import NodeWithScore, TextNode

from app.knowledge_engine.citations.citation_builder import (
    build_citation,
    build_retrieved_chunk,
    build_retrieved_chunks,
)


def _node_with_score(metadata: dict, *, score: float = 0.87, text: str = "chunk text") -> NodeWithScore:
    return NodeWithScore(node=TextNode(text=text, metadata=metadata), score=score)


# --- A: source_document_id is read into Citation.document_id -----------------------


def test_build_citation_populates_document_id_from_source_document_id() -> None:
    node_with_score = _node_with_score(
        {
            "source_document_id": "8f14e45f-ceea-467e-adb2-c9c2af61a832",
            "document_name": "Vendor Services Agreement.pdf",
            "knowledge_source_id": "ks-legal-01",
            "page_number": 3,
            "section": "Termination",
            "chunk_number": 7,
        }
    )

    citation = build_citation(node_with_score)

    assert citation.document_id == "8f14e45f-ceea-467e-adb2-c9c2af61a832"
    # Every other field's existing behavior is unchanged.
    assert citation.document_name == "Vendor Services Agreement.pdf"
    assert citation.knowledge_source_id == "ks-legal-01"
    assert citation.page_number == 3
    assert citation.section == "Termination"
    assert citation.chunk_number == 7
    assert citation.score == 0.87


def test_build_retrieved_chunk_citation_carries_document_id() -> None:
    """RetrievedChunk.citation must carry the same document_id -- proves
    the fix survives the RetrievedChunk wrapping step too, not just
    build_citation() in isolation."""
    node_with_score = _node_with_score(
        {
            "source_document_id": "doc-123",
            "document_name": "Handbook.pdf",
            "knowledge_source_id": "ks-1",
            "chunk_number": 0,
        }
    )

    chunk = build_retrieved_chunk(node_with_score)

    assert chunk.citation.document_id == "doc-123"
    assert chunk.text == "chunk text"


def test_build_retrieved_chunks_preserves_document_id_across_multiple_documents() -> None:
    """Two chunks from two different documents (the actual reported
    scenario: two PDFs pooled in one knowledge source) must keep
    distinguishable document_id values all the way through."""
    legal = _node_with_score(
        {
            "source_document_id": "doc-legal",
            "document_name": "Vendor Services Agreement.pdf",
            "knowledge_source_id": "ks-1",
            "chunk_number": 0,
        },
        text="This Agreement does not disclose a specific contract value.",
    )
    ambiguous = _node_with_score(
        {
            "source_document_id": "doc-ambiguous",
            "document_name": "Vendor Data & Commercial Partnership Agreement.pdf",
            "knowledge_source_id": "ks-1",
            "chunk_number": 0,
        },
        text="Estimated annual contract value: INR 24,000,000.",
    )

    chunks = build_retrieved_chunks([legal, ambiguous])

    assert chunks[0].citation.document_id == "doc-legal"
    assert chunks[1].citation.document_id == "doc-ambiguous"
    assert chunks[0].citation.document_id != chunks[1].citation.document_id


# --- B: missing source_document_id is handled safely, never fabricated -------------


def test_build_citation_defaults_document_id_to_empty_string_when_missing() -> None:
    """No source_document_id in metadata at all (e.g. a chunk indexed
    before this field existed) -- must default safely, exactly like the
    existing knowledge_source_id fallback below it, and must NOT invent
    an id (no random uuid, no reuse of another field's value)."""
    node_with_score = _node_with_score(
        {
            "document_name": "Legacy.pdf",
            "knowledge_source_id": "ks-1",
            "chunk_number": 0,
        }
    )

    citation = build_citation(node_with_score)

    assert citation.document_id == ""
    # Confirms this isn't silently backfilled from some other field.
    assert citation.document_id != citation.document_name
    assert citation.document_id != citation.knowledge_source_id


def test_build_citation_defaults_document_id_when_metadata_is_empty() -> None:
    node_with_score = NodeWithScore(node=TextNode(text="text", metadata={}), score=0.5)

    citation = build_citation(node_with_score)

    assert citation.document_id == ""
    assert citation.document_name == "Unknown document"
    assert citation.knowledge_source_id == ""
