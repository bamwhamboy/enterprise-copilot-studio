"""Tests for Sprint 5's RAG runtime improvements.

These are additive post-processing steps over the existing Sprint 3B
HybridRetriever -- tested here in isolation with plain RetrievedChunk
objects, not requiring a live retriever.
"""

from app.knowledge_engine.models import Citation, RetrievedChunk
from app.knowledge_engine.retrieval.confidence_scorer import ConfidenceScorer
from app.knowledge_engine.retrieval.query_rewriter import QueryRewriter
from app.knowledge_engine.retrieval.reranker import Reranker

_CITATION = Citation(
    document_id="doc1", document_name="doc.pdf", knowledge_source_id="ks1", chunk_number=0
)


def test_query_rewriter_normalizes_whitespace() -> None:
    rewriter = QueryRewriter()
    assert rewriter.rewrite("  what   is  the policy?  ") == "what is the policy?"


def test_query_rewriter_expands_abbreviations() -> None:
    rewriter = QueryRewriter()
    result = rewriter.rewrite("What is our PTO and WFH policy?")
    assert "paid time off" in result
    assert "work from home" in result


def test_reranker_promotes_lexically_relevant_chunk() -> None:
    chunks = [
        RetrievedChunk(text="Travel requires manager approval.", score=0.5, chunk_id="a", citation=_CITATION),
        RetrievedChunk(text="Annual leave is twenty days per year.", score=0.4, chunk_id="b", citation=_CITATION),
    ]
    reranker = Reranker()
    reranked = reranker.rerank("annual leave days", chunks)
    assert reranked[0].chunk_id == "b"


def test_reranker_handles_empty_list() -> None:
    assert Reranker().rerank("query", []) == []


def test_confidence_scorer_empty_is_zero() -> None:
    assert ConfidenceScorer().score([]) == 0.0


def test_confidence_scorer_dominant_top_result_is_high() -> None:
    chunks = [
        RetrievedChunk(text="a", score=0.9, chunk_id="a", citation=_CITATION),
        RetrievedChunk(text="b", score=0.05, chunk_id="b", citation=_CITATION),
    ]
    assert ConfidenceScorer().score(chunks) > 0.8


def test_confidence_scorer_close_scores_is_lower() -> None:
    chunks = [
        RetrievedChunk(text="a", score=0.5, chunk_id="a", citation=_CITATION),
        RetrievedChunk(text="b", score=0.48, chunk_id="b", citation=_CITATION),
    ]
    assert ConfidenceScorer().score(chunks) < 0.6
