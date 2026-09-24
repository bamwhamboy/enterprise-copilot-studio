"""Tests for Graph RAG integration in app/agents/retrieval_node.py.

All fakes, no DB/HTTP/network -- retrieval_node's Graph RAG branch is
fully testable via constructor-injected graph_retriever/fusion fakes
(see make_retrieval_node's `graph_retriever`/`fusion` params, which
exist specifically for this). build_retrieved_chunks is monkeypatched
so tests don't need to construct real LlamaIndex NodeWithScore
objects -- HybridRetriever itself is not exercised here (that's
test_hybrid_retriever.py's job).
"""

import uuid
from types import SimpleNamespace

import pytest

from app.agents.retrieval_node import make_retrieval_node
from app.core.config import Settings, get_settings
from app.knowledge_engine.compression.compression_service import ContextCompressionService
from app.knowledge_engine.models import Citation, RetrievedChunk
from app.knowledge_engine.retrieval.graph_retriever import GraphRetrievalResult
from app.knowledge_engine.retrieval.graph_vector_fusion import FusedResult


def _chunk(chunk_id: str, text: str = "vector chunk text", score: float = 0.8) -> RetrievedChunk:
    return RetrievedChunk(
        text=text,
        score=score,
        chunk_id=chunk_id,
        citation=Citation(
            document_id="doc-1",
            document_name="Doc.pdf",
            knowledge_source_id="ks-1",
            page_number=1,
            chunk_number=0,
            score=score,
        ),
    )


class _FakeHybridRetriever:
    def __init__(self):
        self.calls: list[tuple] = []

    def retrieve(self, query, *, knowledge_source_id=None, document_id=None):
        self.calls.append((query, knowledge_source_id, document_id))
        return "unused-sentinel"  # build_retrieved_chunks is monkeypatched


class _FakeMultiHopRetriever:
    def __init__(self, result=None, raise_error: Exception | None = None):
        self.result = result if result is not None else GraphRetrievalResult()
        self.raise_error = raise_error
        self.calls: list[tuple] = []

    async def retrieve(self, query, *, knowledge_source_id=None, document_id=None):
        self.calls.append((query, knowledge_source_id, document_id))
        if self.raise_error is not None:
            raise self.raise_error
        return self.result


class _FakeFusion:
    def __init__(self, fused_results: list[FusedResult]):
        self.fused_results = fused_results
        self.calls: list[tuple] = []

    def fuse(self, vector_results, graph_result, *, document_id=None, knowledge_source_id=None):
        self.calls.append((vector_results, graph_result, document_id, knowledge_source_id))
        return self.fused_results


def _settings(**overrides) -> Settings:
    return get_settings().model_copy(update=overrides)


def _node(settings, *, graph_retriever=None, fusion=None):
    return make_retrieval_node(
        settings,
        _FakeHybridRetriever(),
        ContextCompressionService(settings),
        graph_retriever=graph_retriever,
        fusion=fusion,
    )


def _base_state(**overrides) -> dict:
    state = {"user_message": "What are the registration fees?"}
    state.update(overrides)
    return state


# --- A. Graph disabled -------------------------------------------------


@pytest.mark.asyncio
async def test_graph_rag_disabled_by_default(monkeypatch) -> None:
    assert get_settings().GRAPH_RAG_ENABLED is False


@pytest.mark.asyncio
async def test_graph_disabled_uses_vector_only_path(monkeypatch) -> None:
    vector_chunk = _chunk("v1")
    monkeypatch.setattr(
        "app.agents.retrieval_node.build_retrieved_chunks", lambda results: [vector_chunk]
    )
    graph_retriever = _FakeMultiHopRetriever()
    fusion = _FakeFusion([])

    settings = _settings(GRAPH_RAG_ENABLED=False)
    node = _node(settings, graph_retriever=graph_retriever, fusion=fusion)
    result = await node(_base_state(document_id=str(uuid.uuid4())))

    assert result["retrieved_chunks"][0].chunk_id == "v1"
    assert graph_retriever.calls == []  # MultiHopRetriever NOT called
    assert fusion.calls == []  # GraphVectorFusion NOT called


# --- B. Graph enabled ----------------------------------------------------


@pytest.mark.asyncio
async def test_graph_enabled_calls_multi_hop_and_fusion(monkeypatch) -> None:
    vector_chunk = _chunk("v1")
    fused_chunk = _chunk("g1", text="graph chunk text")
    monkeypatch.setattr(
        "app.agents.retrieval_node.build_retrieved_chunks", lambda results: [vector_chunk]
    )
    graph_retriever = _FakeMultiHopRetriever()
    fusion = _FakeFusion([FusedResult(chunk=fused_chunk, origin="graph")])

    settings = _settings(GRAPH_RAG_ENABLED=True)
    node = _node(settings, graph_retriever=graph_retriever, fusion=fusion)
    result = await node(_base_state(document_id=str(uuid.uuid4())))

    assert len(graph_retriever.calls) == 1
    assert len(fusion.calls) == 1
    # Fused (not raw vector) results flow through to the downstream path.
    assert result["retrieved_chunks"][0].chunk_id == "g1"


# --- C. Exact scope propagation -------------------------------------------


@pytest.mark.asyncio
async def test_scope_propagated_exactly_from_state(monkeypatch) -> None:
    monkeypatch.setattr("app.agents.retrieval_node.build_retrieved_chunks", lambda results: [])
    document_id = uuid.uuid4()
    knowledge_source_id = uuid.uuid4()
    graph_retriever = _FakeMultiHopRetriever()
    fusion = _FakeFusion([])

    settings = _settings(GRAPH_RAG_ENABLED=True)
    node = _node(settings, graph_retriever=graph_retriever, fusion=fusion)
    await node(
        _base_state(document_id=str(document_id), knowledge_source_id=str(knowledge_source_id))
    )

    _, called_ks_id, called_doc_id = graph_retriever.calls[0]
    assert called_doc_id == document_id
    assert called_ks_id == knowledge_source_id
    _, _, fusion_doc_id, fusion_ks_id = fusion.calls[0]
    assert fusion_doc_id == document_id
    assert fusion_ks_id == knowledge_source_id


# --- D. Missing graph scope -----------------------------------------------


@pytest.mark.asyncio
async def test_missing_scope_skips_graph_rag(monkeypatch) -> None:
    vector_chunk = _chunk("v1")
    monkeypatch.setattr(
        "app.agents.retrieval_node.build_retrieved_chunks", lambda results: [vector_chunk]
    )
    graph_retriever = _FakeMultiHopRetriever()
    fusion = _FakeFusion([])

    settings = _settings(GRAPH_RAG_ENABLED=True)
    node = _node(settings, graph_retriever=graph_retriever, fusion=fusion)
    # No document_id, no knowledge_source_id in state at all.
    result = await node(_base_state())

    assert graph_retriever.calls == []
    assert fusion.calls == []
    assert result["retrieved_chunks"][0].chunk_id == "v1"  # vector retrieval still works


# --- E. Graph failure -------------------------------------------------------


@pytest.mark.asyncio
async def test_graph_retrieval_exception_falls_back_to_vector_results(monkeypatch, caplog) -> None:
    vector_chunk = _chunk("v1")
    monkeypatch.setattr(
        "app.agents.retrieval_node.build_retrieved_chunks", lambda results: [vector_chunk]
    )
    graph_retriever = _FakeMultiHopRetriever(raise_error=RuntimeError("graph db exploded"))
    fusion = _FakeFusion([])

    settings = _settings(GRAPH_RAG_ENABLED=True)
    node = _node(settings, graph_retriever=graph_retriever, fusion=fusion)

    with caplog.at_level("ERROR"):
        result = await node(_base_state(document_id=str(uuid.uuid4())))

    assert result["retrieved_chunks"][0].chunk_id == "v1"  # request did not fail
    assert fusion.calls == []  # never reached fusion
    assert any("Graph RAG" in message for message in caplog.messages)


# --- F. Empty graph result --------------------------------------------------


@pytest.mark.asyncio
async def test_empty_graph_result_preserves_vector_results(monkeypatch) -> None:
    vector_chunk = _chunk("v1")
    monkeypatch.setattr(
        "app.agents.retrieval_node.build_retrieved_chunks", lambda results: [vector_chunk]
    )
    graph_retriever = _FakeMultiHopRetriever(result=GraphRetrievalResult())
    # A real-shaped fusion response for an empty graph result: vector
    # chunk passes through unchanged, origin="vector".
    fusion = _FakeFusion([FusedResult(chunk=vector_chunk, origin="vector")])

    settings = _settings(GRAPH_RAG_ENABLED=True)
    node = _node(settings, graph_retriever=graph_retriever, fusion=fusion)
    result = await node(_base_state(document_id=str(uuid.uuid4())))

    assert result["retrieved_chunks"][0].chunk_id == "v1"


# --- G. Empty vector + graph results ---------------------------------------


@pytest.mark.asyncio
async def test_empty_vector_results_graph_results_still_flow_through(monkeypatch) -> None:
    monkeypatch.setattr("app.agents.retrieval_node.build_retrieved_chunks", lambda results: [])
    graph_chunk = _chunk("g1", text="synthesized from graph evidence")
    graph_retriever = _FakeMultiHopRetriever()
    fusion = _FakeFusion([FusedResult(chunk=graph_chunk, origin="graph")])

    settings = _settings(GRAPH_RAG_ENABLED=True)
    node = _node(settings, graph_retriever=graph_retriever, fusion=fusion)
    result = await node(_base_state(document_id=str(uuid.uuid4())))

    assert result["retrieved_chunks"][0].chunk_id == "g1"


# --- H. Fusion usage (no duplicate logic) -----------------------------------


@pytest.mark.asyncio
async def test_fusion_component_is_the_one_used_no_duplicate_logic(monkeypatch) -> None:
    """Confirms retrieval_node delegates entirely to the injected
    fusion component rather than doing its own merge/dedup/scoring --
    fusion's return value is used verbatim (order and content)."""
    monkeypatch.setattr(
        "app.agents.retrieval_node.build_retrieved_chunks", lambda results: [_chunk("v1")]
    )
    ordered = [
        FusedResult(chunk=_chunk("g2"), origin="graph", fused_score=0.9),
        FusedResult(chunk=_chunk("g1"), origin="graph", fused_score=0.1),
    ]
    graph_retriever = _FakeMultiHopRetriever()
    fusion = _FakeFusion(ordered)

    settings = _settings(GRAPH_RAG_ENABLED=True, RAG_RERANK_ENABLED=False)
    node = _node(settings, graph_retriever=graph_retriever, fusion=fusion)
    result = await node(_base_state(document_id=str(uuid.uuid4())))

    # Exact order fusion returned, not re-derived.
    assert [c.chunk_id for c in result["retrieved_chunks"]][:2] == ["g2", "g1"]


# --- I. Existing downstream behaviour (rerank/top-k/confidence/compression) --


@pytest.mark.asyncio
async def test_downstream_top_k_confidence_compression_apply_to_fused_results(monkeypatch) -> None:
    monkeypatch.setattr("app.agents.retrieval_node.build_retrieved_chunks", lambda results: [])
    fused = [FusedResult(chunk=_chunk(f"g{i}"), origin="graph") for i in range(5)]
    graph_retriever = _FakeMultiHopRetriever()
    fusion = _FakeFusion(fused)

    settings = _settings(GRAPH_RAG_ENABLED=True, RAG_RERANK_ENABLED=False, HYBRID_FINAL_TOP_K=2)
    node = _node(settings, graph_retriever=graph_retriever, fusion=fusion)
    result = await node(_base_state(document_id=str(uuid.uuid4())))

    assert len(result["retrieved_chunks"]) == 2  # existing top-k still applies
    assert "confidence" in result  # existing confidence output contract preserved


@pytest.mark.asyncio
async def test_reranker_accepts_fused_results_without_error(monkeypatch) -> None:
    monkeypatch.setattr("app.agents.retrieval_node.build_retrieved_chunks", lambda results: [])
    fused = [FusedResult(chunk=_chunk("g1", text="registration fees are due"), origin="graph")]
    graph_retriever = _FakeMultiHopRetriever()
    fusion = _FakeFusion(fused)

    settings = _settings(GRAPH_RAG_ENABLED=True, RAG_RERANK_ENABLED=True)
    node = _node(settings, graph_retriever=graph_retriever, fusion=fusion)
    result = await node(_base_state(document_id=str(uuid.uuid4())))

    assert result["retrieved_chunks"][0].chunk_id == "g1"  # reranker ran, no crash


# --- J. Existing retrieval-node behaviour preserved -------------------------


@pytest.mark.asyncio
async def test_state_output_keys_unchanged(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.agents.retrieval_node.build_retrieved_chunks", lambda results: [_chunk("v1")]
    )
    settings = _settings(GRAPH_RAG_ENABLED=False)
    node = _node(settings)
    result = await node(_base_state())

    assert set(result.keys()) == {"retrieved_chunks", "confidence"}
