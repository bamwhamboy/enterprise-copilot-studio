"""Unit tests for AdaptiveRetrievalOrchestrator. All fakes, no DB."""

import uuid

import pytest

from app.core.config import get_settings
from app.knowledge_engine.models import Citation, RetrievedChunk
from app.knowledge_engine.retrieval.adaptive_retrieval_orchestrator import (
    AdaptiveRetrievalOrchestrator,
    RetrievalMode,
    RoutingContext,
    jev_mode_selector,
)
from app.knowledge_engine.retrieval.graph_retriever import GraphRetrievalResult
from app.knowledge_engine.retrieval.graph_vector_fusion import FusedResult


def _chunk(chunk_id: str, text: str = "text", score: float = 0.5) -> RetrievedChunk:
    return RetrievedChunk(
        text=text, score=score, chunk_id=chunk_id,
        citation=Citation(document_id="d", document_name="D", knowledge_source_id="k",
                           page_number=1, chunk_number=0, score=score),
    )


class _FakeHybrid:
    def __init__(self, chunks=None):
        self.chunks = chunks if chunks is not None else [_chunk("v1")]
        self.calls = []

    def retrieve(self, query, *, knowledge_source_id=None, document_id=None):
        self.calls.append((query, knowledge_source_id, document_id))
        return "sentinel"


class _FakeGraph:
    def __init__(self, result=None, raise_error=None):
        self.result = result if result is not None else GraphRetrievalResult()
        self.raise_error = raise_error
        self.calls = []

    async def retrieve(self, query, *, knowledge_source_id=None, document_id=None):
        self.calls.append((query, knowledge_source_id, document_id))
        if self.raise_error:
            raise self.raise_error
        return self.result


class _FakeFusion:
    def __init__(self, results=None, raise_error=None):
        self.results = results if results is not None else []
        self.raise_error = raise_error
        self.calls = []

    def fuse(self, vector_results, graph_result, *, document_id=None, knowledge_source_id=None):
        self.calls.append((vector_results, graph_result, document_id, knowledge_source_id))
        if self.raise_error:
            raise self.raise_error
        return self.results


def _settings(**overrides):
    return get_settings().model_copy(update=overrides)


def _patch_build_chunks(monkeypatch, chunks):
    monkeypatch.setattr(
        "app.knowledge_engine.retrieval.adaptive_retrieval_orchestrator.build_retrieved_chunks",
        lambda results: chunks,
    )


# --- Mode selection: JEV adapter ------------------------------------------


def test_jev_selector_relationship_query_selects_graph():
    ctx = RoutingContext(
        query="What is the relationship between Acme and Globex?",
        document_id=uuid.uuid4(),
        knowledge_source_id=None,
    )
    assert jev_mode_selector(ctx) == RetrievalMode.GRAPH


def test_jev_selector_multi_hop_query_selects_hybrid_graph():
    ctx = RoutingContext(
        query="How does A affect B, which in turn impacts C?",
        document_id=uuid.uuid4(),
        knowledge_source_id=None,
    )
    assert jev_mode_selector(ctx) == RetrievalMode.HYBRID_GRAPH


def test_jev_selector_plain_query_selects_hybrid():
    ctx = RoutingContext(
        query="What is the registration fee?",
        document_id=uuid.uuid4(),
        knowledge_source_id=None,
    )
    assert jev_mode_selector(ctx) == RetrievalMode.HYBRID


def test_jev_selector_is_deterministic():
    ctx = RoutingContext(
        query="relationship between Acme and Globex",
        document_id=uuid.uuid4(),
        knowledge_source_id=None,
    )
    assert jev_mode_selector(ctx) == jev_mode_selector(ctx) == RetrievalMode.GRAPH


# --- Master flag + scope enforcement (never delegated to selector) ---------


@pytest.mark.asyncio
async def test_graph_rag_disabled_forces_hybrid_even_with_relationship_query(monkeypatch):
    _patch_build_chunks(monkeypatch, [_chunk("v1")])
    hybrid, graph, fusion = _FakeHybrid(), _FakeGraph(), _FakeFusion()
    orch = AdaptiveRetrievalOrchestrator(
        _settings(GRAPH_RAG_ENABLED=False), hybrid, graph, fusion
    )

    result = await orch.retrieve("relationship between Acme and Globex", document_id=uuid.uuid4())

    assert [c.chunk_id for c in result] == ["v1"]
    assert graph.calls == []
    assert fusion.calls == []


@pytest.mark.asyncio
async def test_missing_scope_forces_hybrid_even_with_relationship_query(monkeypatch):
    _patch_build_chunks(monkeypatch, [_chunk("v1")])
    hybrid, graph, fusion = _FakeHybrid(), _FakeGraph(), _FakeFusion()
    orch = AdaptiveRetrievalOrchestrator(_settings(GRAPH_RAG_ENABLED=True), hybrid, graph, fusion)

    result = await orch.retrieve("relationship between Acme and Globex")  # no scope

    assert [c.chunk_id for c in result] == ["v1"]
    assert graph.calls == []
    assert fusion.calls == []


@pytest.mark.asyncio
async def test_missing_graph_components_forces_hybrid(monkeypatch):
    _patch_build_chunks(monkeypatch, [_chunk("v1")])
    orch = AdaptiveRetrievalOrchestrator(_settings(GRAPH_RAG_ENABLED=True), _FakeHybrid())

    result = await orch.retrieve("relationship between Acme and Globex", document_id=uuid.uuid4())

    assert [c.chunk_id for c in result] == ["v1"]


# --- Mode HYBRID -------------------------------------------------------------


@pytest.mark.asyncio
async def test_hybrid_mode_calls_only_hybrid_retriever(monkeypatch):
    _patch_build_chunks(monkeypatch, [_chunk("v1")])
    hybrid, graph, fusion = _FakeHybrid(), _FakeGraph(), _FakeFusion()
    orch = AdaptiveRetrievalOrchestrator(_settings(GRAPH_RAG_ENABLED=True), hybrid, graph, fusion)

    result = await orch.retrieve("What is the registration fee?", document_id=uuid.uuid4())

    assert len(hybrid.calls) == 1
    assert graph.calls == []
    assert fusion.calls == []
    assert [c.chunk_id for c in result] == ["v1"]


# --- Mode GRAPH ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_graph_mode_calls_graph_and_fusion_not_hybrid(monkeypatch):
    _patch_build_chunks(monkeypatch, [])
    hybrid = _FakeHybrid()
    graph = _FakeGraph()
    fusion = _FakeFusion([FusedResult(chunk=_chunk("g1"), origin="graph")])
    orch = AdaptiveRetrievalOrchestrator(_settings(GRAPH_RAG_ENABLED=True), hybrid, graph, fusion)

    result = await orch.retrieve(
        "relationship between Acme and Globex", document_id=uuid.uuid4()
    )

    assert hybrid.calls == []
    assert len(graph.calls) == 1
    assert fusion.calls[0][0] == []  # fused with empty vector_results
    assert [c.chunk_id for c in result] == ["g1"]


@pytest.mark.asyncio
async def test_graph_mode_failure_falls_back_to_hybrid_retriever(monkeypatch, caplog):
    _patch_build_chunks(monkeypatch, [_chunk("v1")])
    hybrid = _FakeHybrid()
    graph = _FakeGraph(raise_error=RuntimeError("graph db down"))
    fusion = _FakeFusion()
    orch = AdaptiveRetrievalOrchestrator(_settings(GRAPH_RAG_ENABLED=True), hybrid, graph, fusion)

    with caplog.at_level("ERROR"):
        result = await orch.retrieve(
            "relationship between Acme and Globex", document_id=uuid.uuid4()
        )

    assert len(hybrid.calls) == 1  # reactive fallback call happened
    assert [c.chunk_id for c in result] == ["v1"]
    assert any("Graph-only" in m for m in caplog.messages)


# --- Mode HYBRID_GRAPH --------------------------------------------------------


@pytest.mark.asyncio
async def test_hybrid_graph_mode_calls_both_and_fuses(monkeypatch):
    _patch_build_chunks(monkeypatch, [_chunk("v1")])
    hybrid = _FakeHybrid([_chunk("v1")])
    graph = _FakeGraph()
    fusion = _FakeFusion([FusedResult(chunk=_chunk("g1"), origin="graph"),
                          FusedResult(chunk=_chunk("v1"), origin="vector")])
    orch = AdaptiveRetrievalOrchestrator(_settings(GRAPH_RAG_ENABLED=True), hybrid, graph, fusion)

    result = await orch.retrieve(
        "How does A affect B, which in turn impacts C?", document_id=uuid.uuid4()
    )

    assert len(hybrid.calls) == 1
    assert len(graph.calls) == 1
    assert len(fusion.calls) == 1
    assert fusion.calls[0][0] != []  # fused WITH real vector results this time
    assert {c.chunk_id for c in result} == {"g1", "v1"}


@pytest.mark.asyncio
async def test_hybrid_graph_mode_failure_falls_back_to_vector_results(monkeypatch, caplog):
    _patch_build_chunks(monkeypatch, [_chunk("v1")])
    hybrid = _FakeHybrid([_chunk("v1")])
    graph = _FakeGraph(raise_error=RuntimeError("graph db down"))
    fusion = _FakeFusion()
    orch = AdaptiveRetrievalOrchestrator(_settings(GRAPH_RAG_ENABLED=True), hybrid, graph, fusion)

    with caplog.at_level("ERROR"):
        result = await orch.retrieve(
            "How does A affect B, which in turn impacts C?", document_id=uuid.uuid4()
        )

    assert [c.chunk_id for c in result] == ["v1"]  # already-retrieved vector results
    assert any("Graph retrieval/fusion failed" in m for m in caplog.messages)


# --- Scope propagation exactness ---------------------------------------------


@pytest.mark.asyncio
async def test_scope_propagated_exactly_to_graph_and_fusion(monkeypatch):
    _patch_build_chunks(monkeypatch, [])
    doc_id, ks_id = uuid.uuid4(), uuid.uuid4()
    hybrid, graph = _FakeHybrid(), _FakeGraph()
    fusion = _FakeFusion([])
    orch = AdaptiveRetrievalOrchestrator(_settings(GRAPH_RAG_ENABLED=True), hybrid, graph, fusion)

    await orch.retrieve(
        "relationship between Acme and Globex", document_id=doc_id, knowledge_source_id=ks_id
    )

    assert graph.calls[0][1:] == (ks_id, doc_id)
    assert fusion.calls[0][2:] == (doc_id, ks_id)
