"""Tests for Graph + Vector retrieval fusion (Sprint 2):
GraphVectorFusion (app/knowledge_engine/retrieval/graph_vector_fusion.py).

Most tests here construct RetrievedChunk/GraphRetrievalResult objects
directly in memory -- fusion itself makes no DB/LLM/embedding calls,
so most of its behavior needs no database at all. The two scope
-isolation tests are the exception: they run the real GraphRetriever
against a real database first, since "does fusion preserve
GraphRetriever's isolation guarantee" can only be meaningfully tested
by actually exercising that guarantee, not by hand-constructing
already-correct input.
"""

import uuid

import pytest
from httpx import AsyncClient

from app.database.session import AsyncSessionLocal
from app.knowledge_engine.models import Citation, RetrievedChunk
from app.knowledge_engine.retrieval.graph_retriever import (
    GraphEntityMatch,
    GraphEvidenceInfo,
    GraphRelationshipResult,
    GraphRetrievalResult,
    GraphRetriever,
)
from app.knowledge_engine.retrieval.graph_vector_fusion import GraphVectorFusion
from app.models.graph import GraphEntity, GraphRelationship
from app.repositories.graph_repository import (
    GraphEntityRepository,
    GraphEvidenceRepository,
    GraphRelationshipRepository,
)

KS_BASE = "/api/v1/knowledge-sources"
DOC_BASE = "/api/v1/documents"


def _auth_headers(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _create_document(
    client: AsyncClient, headers: dict, name: str, *, knowledge_source_id: str | None = None
) -> tuple[uuid.UUID, uuid.UUID]:
    if knowledge_source_id is None:
        ks_response = await client.post(
            KS_BASE, json={"name": f"{name} Source"}, headers=headers
        )
        knowledge_source_id = ks_response.json()["id"]

    doc_response = await client.post(
        DOC_BASE,
        json={"knowledge_source_id": knowledge_source_id, "name": name, "status": "indexed"},
        headers=headers,
    )
    return uuid.UUID(doc_response.json()["id"]), uuid.UUID(knowledge_source_id)


def _chunk(chunk_id: str, text: str = "some chunk text", score: float = 0.8) -> RetrievedChunk:
    return RetrievedChunk(
        text=text,
        score=score,
        chunk_id=chunk_id,
        citation=Citation(
            document_id="doc-1",
            document_name="Fee Schedule.pdf",
            knowledge_source_id="ks-1",
            page_number=1,
            chunk_number=0,
            score=score,
        ),
    )


def _entity_match(name: str, canonical_name: str, *, depth: int = 0) -> GraphEntityMatch:
    return GraphEntityMatch(
        entity_id=uuid.uuid4(),
        name=name,
        canonical_name=canonical_name,
        entity_type="organization",
        depth=depth,
    )


def _relationship(
    *,
    chunk_ids: list[str],
    relationship_type: str = "provides_services_to",
    depth: int = 1,
    source_name: str = "Acme Corp",
    target_name: str = "Globex LLC",
    confidence: float | None = 0.9,
    page_number: int | None = 3,
) -> GraphRelationshipResult:
    return GraphRelationshipResult(
        relationship_id=uuid.uuid4(),
        relationship_type=relationship_type,
        source=_entity_match(source_name, source_name.lower()),
        target=_entity_match(target_name, target_name.lower(), depth=depth),
        confidence=confidence,
        depth=depth,
        evidence=[
            GraphEvidenceInfo(
                chunk_id=chunk_id,
                page_number=page_number,
                source_text=f"Evidence text for {chunk_id}",
            )
            for chunk_id in chunk_ids
        ],
    )


# --- Vector-only / graph-only / empty --------------------------------------


def test_vector_only_result_is_preserved() -> None:
    fusion = GraphVectorFusion()
    vector_results = [_chunk("chunk-1"), _chunk("chunk-2", score=0.5)]

    fused = fusion.fuse(vector_results, None)

    assert len(fused) == 2
    assert all(r.origin == "vector" for r in fused)
    assert all(r.graph_provenance == [] for r in fused)
    assert {r.chunk.chunk_id for r in fused} == {"chunk-1", "chunk-2"}


def test_graph_only_result_synthesizes_a_chunk() -> None:
    fusion = GraphVectorFusion()
    graph_result = GraphRetrievalResult(relationships=[_relationship(chunk_ids=["chunk-9"])])

    fused = fusion.fuse([], graph_result)

    assert len(fused) == 1
    result = fused[0]
    assert result.origin == "graph"
    assert result.chunk.chunk_id == "chunk-9"
    assert result.chunk.text == "Evidence text for chunk-9"
    assert len(result.graph_provenance) == 1


def test_empty_vector_and_empty_graph_returns_empty() -> None:
    fusion = GraphVectorFusion()
    assert fusion.fuse([], None) == []
    assert fusion.fuse([], GraphRetrievalResult()) == []


# --- Overlap / deduplication ------------------------------------------------


def test_overlapping_chunk_is_merged_not_duplicated() -> None:
    """The same chunk_id appearing in both vector results and graph
    evidence must produce exactly one FusedResult, origin="both", not
    two separate entries."""
    fusion = GraphVectorFusion()
    vector_results = [_chunk("chunk-1", text="real vector text", score=0.7)]
    graph_result = GraphRetrievalResult(relationships=[_relationship(chunk_ids=["chunk-1"])])

    fused = fusion.fuse(vector_results, graph_result)

    assert len(fused) == 1
    result = fused[0]
    assert result.origin == "both"
    # The REAL vector-retrieved chunk's text wins over a synthesized one.
    assert result.chunk.text == "real vector text"
    assert len(result.graph_provenance) == 1


def test_chunk_evidence_for_two_relationships_is_not_duplicated() -> None:
    fusion = GraphVectorFusion()
    rel_a = _relationship(chunk_ids=["chunk-1"], relationship_type="provides_services_to")
    rel_b = _relationship(chunk_ids=["chunk-1"], relationship_type="distinct_from", depth=2)
    graph_result = GraphRetrievalResult(relationships=[rel_a, rel_b])

    fused = fusion.fuse([], graph_result)

    assert len(fused) == 1
    assert len(fused[0].graph_provenance) == 2
    provenance_types = {p.relationship_type for p in fused[0].graph_provenance}
    assert provenance_types == {"provides_services_to", "distinct_from"}


def test_relationship_with_multiple_evidence_chunks_produces_separate_results() -> None:
    """One relationship whose evidence spans two different chunks must
    surface as two separate fused results, each carrying that
    relationship's provenance."""
    fusion = GraphVectorFusion()
    graph_result = GraphRetrievalResult(
        relationships=[_relationship(chunk_ids=["chunk-1", "chunk-2"])]
    )

    fused = fusion.fuse([], graph_result)

    assert {r.chunk.chunk_id for r in fused} == {"chunk-1", "chunk-2"}
    assert all(len(r.graph_provenance) == 1 for r in fused)


# --- Deterministic ranking + limit -----------------------------------------


def test_ranking_is_deterministic_across_repeated_calls() -> None:
    fusion = GraphVectorFusion()
    vector_results = [_chunk(f"chunk-{i}", score=0.1 * i) for i in range(1, 6)]
    graph_result = GraphRetrievalResult(relationships=[_relationship(chunk_ids=["chunk-3"])])

    first = fusion.fuse(vector_results, graph_result)
    second = fusion.fuse(vector_results, graph_result)

    assert [r.chunk.chunk_id for r in first] == [r.chunk.chunk_id for r in second]
    assert [r.fused_score for r in first] == [r.fused_score for r in second]


def test_higher_combined_score_ranks_first() -> None:
    fusion = GraphVectorFusion()
    # chunk-low: vector only, low score. chunk-high: vector low score
    # but ALSO graph evidence at depth=1 -- combined score should win.
    vector_results = [_chunk("chunk-low", score=0.2), _chunk("chunk-high", score=0.2)]
    graph_result = GraphRetrievalResult(
        relationships=[_relationship(chunk_ids=["chunk-high"], depth=1)]
    )

    fused = fusion.fuse(vector_results, graph_result)

    assert fused[0].chunk.chunk_id == "chunk-high"
    assert fused[0].fused_score > fused[1].fused_score


def test_final_result_limit_is_respected() -> None:
    fusion = GraphVectorFusion(limit=2)
    vector_results = [_chunk(f"chunk-{i}", score=0.1 * i) for i in range(1, 6)]

    fused = fusion.fuse(vector_results, None)

    assert len(fused) == 2
    # Top-2 by score: chunk-5 (0.5), chunk-4 (0.4).
    assert [r.chunk.chunk_id for r in fused] == ["chunk-5", "chunk-4"]


def test_fuse_call_can_override_configured_limit() -> None:
    fusion = GraphVectorFusion(limit=10)
    vector_results = [_chunk(f"chunk-{i}") for i in range(1, 6)]

    fused = fusion.fuse(vector_results, None, limit=1)

    assert len(fused) == 1


def test_configurable_weights_change_ranking() -> None:
    vector_results = [_chunk("chunk-vector-strong", score=1.0)]
    graph_result = GraphRetrievalResult(
        relationships=[_relationship(chunk_ids=["chunk-graph-strong"], depth=1)]
    )

    vector_heavy = GraphVectorFusion(vector_weight=1.0, graph_weight=0.0)
    fused_vector_heavy = vector_heavy.fuse(vector_results, graph_result)
    assert fused_vector_heavy[0].chunk.chunk_id == "chunk-vector-strong"

    graph_heavy = GraphVectorFusion(vector_weight=0.0, graph_weight=1.0)
    fused_graph_heavy = graph_heavy.fuse(vector_results, graph_result)
    assert fused_graph_heavy[0].chunk.chunk_id == "chunk-graph-strong"


# --- Graph provenance / citation preservation -------------------------------


def test_graph_provenance_preserves_entity_relationship_and_evidence_fields() -> None:
    fusion = GraphVectorFusion()
    graph_result = GraphRetrievalResult(
        relationships=[
            _relationship(
                chunk_ids=["chunk-1"],
                relationship_type="provides_services_to",
                source_name="Acme Corp",
                target_name="Globex LLC",
                depth=2,
                confidence=0.77,
                page_number=5,
            )
        ]
    )

    fused = fusion.fuse([], graph_result)

    provenance = fused[0].graph_provenance[0]
    assert provenance.relationship_type == "provides_services_to"
    assert provenance.source_entity_name == "Acme Corp"
    assert provenance.target_entity_name == "Globex LLC"
    assert provenance.depth == 2
    assert provenance.confidence == pytest.approx(0.77)
    assert provenance.chunk_id == "chunk-1"
    assert provenance.page_number == 5
    assert provenance.source_text == "Evidence text for chunk-1"


def test_vector_citation_metadata_is_preserved_through_fusion() -> None:
    fusion = GraphVectorFusion()
    chunk = _chunk("chunk-1")

    fused = fusion.fuse([chunk], None)

    assert fused[0].chunk.citation.document_name == "Fee Schedule.pdf"
    assert fused[0].chunk.citation.knowledge_source_id == "ks-1"
    assert fused[0].chunk.citation.page_number == 1


# --- Scope isolation (integration, through the real GraphRetriever) --------


async def _make_entity(session, document_id, name, canonical_name, entity_type="organization"):
    entity = GraphEntity(
        document_id=document_id, name=name, canonical_name=canonical_name, entity_type=entity_type
    )
    session.add(entity)
    await session.flush()
    return entity


async def _make_relationship_row(session, document_id, source, target, relationship_type):
    rel = GraphRelationship(
        document_id=document_id,
        source_entity_id=source.id,
        target_entity_id=target.id,
        relationship_type=relationship_type,
    )
    session.add(rel)
    await session.flush()
    return rel


def _real_graph_retriever(session) -> GraphRetriever:
    return GraphRetriever(
        GraphEntityRepository(session),
        GraphRelationshipRepository(session),
        GraphEvidenceRepository(session),
    )


@pytest.mark.asyncio
async def test_fusion_preserves_document_scope_isolation(
    client: AsyncClient, register_and_login
) -> None:
    """GraphRetriever scoped to doc_a must never surface doc_b's
    entities; fusing that (already-correct) result must not
    reintroduce them either."""
    headers = _auth_headers(await register_and_login(email="fusionscope1@example.com"))
    doc_a, _ = await _create_document(client, headers, "Fusion Scope Doc A")
    doc_b, _ = await _create_document(client, headers, "Fusion Scope Doc B")

    async with AsyncSessionLocal() as session:
        acme_a = await _make_entity(session, doc_a, "Acme Corp", "acme corp")
        globex_a = await _make_entity(session, doc_a, "Globex LLC", "globex llc")
        await _make_relationship_row(session, doc_a, acme_a, globex_a, "provides_services_to")

        secret_b = await _make_entity(session, doc_b, "Confidential Entity", "confidential entity")
        await session.commit()

    async with AsyncSessionLocal() as session:
        graph_result = await _real_graph_retriever(session).retrieve(
            "Tell me about Acme Corp", document_id=doc_a
        )

    fusion = GraphVectorFusion()
    fused = fusion.fuse([], graph_result, document_id=doc_a)

    all_entity_names = {p.source_entity_name for r in fused for p in r.graph_provenance} | {
        p.target_entity_name for r in fused for p in r.graph_provenance
    }
    assert "Confidential Entity" not in all_entity_names
    assert secret_b.id != acme_a.id  # sanity: fixtures actually distinct


@pytest.mark.asyncio
async def test_fusion_preserves_knowledge_source_scope_isolation(
    client: AsyncClient, register_and_login
) -> None:
    headers = _auth_headers(await register_and_login(email="fusionscope2@example.com"))
    doc_a, ks_id = await _create_document(client, headers, "Fusion KS Doc A")
    other_doc, other_ks_id = await _create_document(client, headers, "Fusion Other KS Doc")

    async with AsyncSessionLocal() as session:
        acme_a = await _make_entity(session, doc_a, "Acme Corp", "acme corp")
        globex_a = await _make_entity(session, doc_a, "Globex LLC", "globex llc")
        await _make_relationship_row(session, doc_a, acme_a, globex_a, "provides_services_to")

        secret_other = await _make_entity(
            session, other_doc, "Confidential Entity", "confidential entity"
        )
        await session.commit()

    async with AsyncSessionLocal() as session:
        graph_result = await _real_graph_retriever(session).retrieve(
            "Tell me about Acme Corp", knowledge_source_id=ks_id
        )

    fusion = GraphVectorFusion()
    fused = fusion.fuse([], graph_result, knowledge_source_id=ks_id)

    all_entity_names = {p.source_entity_name for r in fused for p in r.graph_provenance} | {
        p.target_entity_name for r in fused for p in r.graph_provenance
    }
    assert "Confidential Entity" not in all_entity_names
    assert secret_other.id != acme_a.id


# --- Validation --------------------------------------------------------------


def test_fusion_rejects_negative_weights() -> None:
    with pytest.raises(ValueError):
        GraphVectorFusion(vector_weight=-1.0)


def test_fusion_rejects_zero_limit() -> None:
    with pytest.raises(ValueError):
        GraphVectorFusion(limit=0)
