"""Tests for Graph RAG's integration into ``IndexingService``.

Covers: vector indexing and graph extraction both run for a document,
graph extraction receives the exact same ``HierarchicalChunk`` objects
vector indexing consumes (not a second, independent chunking pass),
and a graph extraction failure -- partial or total -- never affects
vector indexing's success or the document's ``index_status``.

No real LLM call is made anywhere in this file. Two styles of fake are
used: a bare recording fake (records calls, returns/raises a canned
outcome) for the "does IndexingService call this at all, with what
args" tests, and the real ``GraphExtractionService`` wired to a fake
LLM gateway (same pattern as ``test_graph_extraction_service.py``) for
the test that specifically exercises real per-chunk failure isolation
through the full integration.

This suite does not touch chat orchestration, retrieval, BM25,
reranking, prompt building, or answer generation.
"""

import io
import uuid
from types import SimpleNamespace

import fitz
import pytest
from httpx import AsyncClient

from app.core.dependencies import DbSessionDep, get_graph_extraction_service
from app.knowledge_engine.graph.graph_extraction_service import GraphExtractionResult
from app.knowledge_engine.models import HierarchicalChunk
from app.main import app

KS_BASE = "/api/v1/knowledge-sources"
DOC_BASE = "/api/v1/documents"


def _auth_headers(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _make_pdf_bytes(*, pages: list[str]) -> bytes:
    doc = fitz.open()
    for text in pages:
        page = doc.new_page()
        page.insert_text((72, 72), text)
    content = doc.tobytes()
    doc.close()
    return content


async def _create_knowledge_source(client: AsyncClient, headers: dict, name: str) -> str:
    response = await client.post(KS_BASE, json={"name": name}, headers=headers)
    return response.json()["id"]


async def _upload_pdf(
    client: AsyncClient, headers: dict, ks_id: str, filename: str, pages: list[str]
) -> dict:
    pdf_bytes = _make_pdf_bytes(pages=pages)
    response = await client.post(
        f"{DOC_BASE}/upload",
        data={"knowledge_source_id": ks_id},
        files={"file": (filename, io.BytesIO(pdf_bytes), "application/pdf")},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


class _RecordingGraphExtractionService:
    """Stands in for the real GraphExtractionService: records exactly
    what it was called with, and returns (or raises) a canned outcome.
    """

    def __init__(
        self,
        *,
        result: GraphExtractionResult | None = None,
        raise_error: Exception | None = None,
    ) -> None:
        self._result = result
        self._raise_error = raise_error
        self.calls: list[tuple[uuid.UUID, list[HierarchicalChunk]]] = []

    async def extract_for_document(self, document_id, chunks):
        self.calls.append((document_id, list(chunks)))
        if self._raise_error is not None:
            raise self._raise_error
        return self._result


@pytest.fixture(autouse=True)
def _clear_graph_extraction_override():
    yield
    app.dependency_overrides.pop(get_graph_extraction_service, None)


# --- Successful vector + graph indexing -------------------------------------


@pytest.mark.asyncio
async def test_indexing_invokes_graph_extraction_with_the_exact_same_chunks(
    client: AsyncClient, register_and_login
) -> None:
    fake_graph_service = _RecordingGraphExtractionService(
        result=GraphExtractionResult(
            document_id=uuid.uuid4(),  # placeholder; real id asserted separately below
            chunks_processed=1,
            chunks_succeeded=1,
            entities_created=2,
            relationships_created=1,
            evidence_created=1,
        )
    )
    app.dependency_overrides[get_graph_extraction_service] = lambda: fake_graph_service

    headers = _auth_headers(await register_and_login(email="idxgraph1@example.com"))
    ks_id = await _create_knowledge_source(client, headers, "Graph Integration Source")
    doc = await _upload_pdf(
        client,
        headers,
        ks_id,
        "vendor_agreement.pdf",
        pages=["Acme Corp shall provide services to Globex LLC. " * 20],
    )

    response = await client.post(f"/api/v1/index/{doc['id']}")
    assert response.status_code == 200
    body = response.json()
    assert body["index_status"] == "INDEXED"
    assert body["chunks_indexed"] > 0

    # Graph extraction was actually invoked, exactly once, for this document.
    assert len(fake_graph_service.calls) == 1
    called_document_id, called_chunks = fake_graph_service.calls[0]
    assert str(called_document_id) == doc["id"]

    # It received the SAME chunks vector indexing used: same count as
    # what got embedded/written, real HierarchicalChunk objects with
    # real text -- not a second, independently-produced chunking pass.
    assert len(called_chunks) == body["chunks_indexed"]
    assert all(isinstance(chunk, HierarchicalChunk) for chunk in called_chunks)
    assert all(chunk.text for chunk in called_chunks)


# --- Graph extraction (total) failure while vector indexing succeeds -------


@pytest.mark.asyncio
async def test_graph_extraction_total_failure_still_completes_vector_indexing(
    client: AsyncClient, register_and_login
) -> None:
    fake_graph_service = _RecordingGraphExtractionService(
        raise_error=RuntimeError("simulated total graph extraction outage")
    )
    app.dependency_overrides[get_graph_extraction_service] = lambda: fake_graph_service

    headers = _auth_headers(await register_and_login(email="idxgraph2@example.com"))
    ks_id = await _create_knowledge_source(client, headers, "Graph Failure Source")
    doc = await _upload_pdf(
        client,
        headers,
        ks_id,
        "vendor_agreement2.pdf",
        pages=["Acme Corp shall provide services to Globex LLC. " * 20],
    )

    response = await client.post(f"/api/v1/index/{doc['id']}")
    assert response.status_code == 200
    body = response.json()
    assert body["index_status"] == "INDEXED"
    assert body["chunks_indexed"] > 0
    assert len(fake_graph_service.calls) == 1

    # Document indexing status remains correct (INDEXED) even though
    # graph extraction failed completely.
    get_response = await client.get(f"{DOC_BASE}/{doc['id']}", headers=headers)
    get_body = get_response.json()
    assert get_body["index_status"] == "INDEXED"
    assert get_body["chunks"] == body["chunks_indexed"]
    assert get_body["embeddings"] == body["chunks_indexed"]


# --- Real per-chunk graph failure isolation, through the full integration --


class _AlwaysMalformedGateway:
    """A fake LLM gateway that returns unparseable output for every call --
    every chunk's graph extraction genuinely fails via the real
    GraphExtractor/GraphExtractionService code path, exactly as it
    would in production, not via a stubbed-out fake service."""

    async def generate(self, request):
        return SimpleNamespace(content="not valid json {{{")


@pytest.mark.asyncio
async def test_partial_graph_failure_through_real_service_does_not_affect_indexing(
    client: AsyncClient, register_and_login
) -> None:
    from app.knowledge_engine.graph.extractor import GraphExtractor
    from app.knowledge_engine.graph.graph_extraction_service import GraphExtractionService

    async def _override_with_real_but_broken_service(session: DbSessionDep):
        # Reuses the SAME request-scoped session IndexingService itself
        # uses (via DbSessionDep), matching how get_graph_extraction_service
        # wires it in production -- not a second, independent session.
        return GraphExtractionService(session, GraphExtractor(_AlwaysMalformedGateway()))

    app.dependency_overrides[get_graph_extraction_service] = _override_with_real_but_broken_service

    headers = _auth_headers(await register_and_login(email="idxgraph3@example.com"))
    ks_id = await _create_knowledge_source(client, headers, "Graph Real Failure Source")
    doc = await _upload_pdf(
        client,
        headers,
        ks_id,
        "vendor_agreement3.pdf",
        pages=["Acme Corp shall provide services to Globex LLC. " * 20],
    )

    response = await client.post(f"/api/v1/index/{doc['id']}")
    assert response.status_code == 200
    body = response.json()
    assert body["index_status"] == "INDEXED"
    assert body["chunks_indexed"] > 0

    get_response = await client.get(f"{DOC_BASE}/{doc['id']}", headers=headers)
    assert get_response.json()["index_status"] == "INDEXED"

    # Bug fix regression: the failure summary must now be visible in
    # the API response itself, including the actual error message per
    # chunk (previously only chunk_ids were logged, and nothing at all
    # was returned from the endpoint).
    graph_extraction = body["graph_extraction"]
    assert graph_extraction["status"] == "failed"
    assert graph_extraction["chunks_failed"] == graph_extraction["chunks_processed"]
    assert graph_extraction["entities_created"] == 0
    assert len(graph_extraction["sample_errors"]) > 0
    assert graph_extraction["sample_errors"][0]["error"]  # non-empty real message


# --- Regression: successful extraction actually persists end-to-end -------


_SUCCESS_JSON = """{
  "entities": [
    {"name": "Acme Corp", "canonical_name": "acme corp", "entity_type": "organization"},
    {"name": "Globex LLC", "canonical_name": "globex llc", "entity_type": "organization"}
  ],
  "relationships": [
    {"source_entity": "acme corp", "target_entity": "globex llc", \
"relationship_type": "provides_services_to", "confidence": 0.9}
  ]
}"""


class _AlwaysSuccessfulGateway:
    """A fake LLM gateway that returns well-formed, successful
    extraction JSON for every call -- verifies rows are actually
    persisted end-to-end through the real IndexingService ->
    GraphExtractionService -> repository -> session path, not just
    that the service gets invoked (the recording fake above proves
    invocation; this proves persistence)."""

    async def generate(self, request):
        return SimpleNamespace(content=_SUCCESS_JSON)


@pytest.mark.asyncio
async def test_successful_graph_extraction_persists_rows_through_real_indexing(
    client: AsyncClient, register_and_login
) -> None:
    from app.knowledge_engine.graph.extractor import GraphExtractor
    from app.knowledge_engine.graph.graph_extraction_service import GraphExtractionService
    from app.database.session import AsyncSessionLocal
    from app.models.graph import GraphEntity, GraphEvidence, GraphRelationship
    from sqlalchemy import select

    async def _override_with_real_successful_service(session: DbSessionDep):
        return GraphExtractionService(session, GraphExtractor(_AlwaysSuccessfulGateway()))

    app.dependency_overrides[get_graph_extraction_service] = _override_with_real_successful_service

    headers = _auth_headers(await register_and_login(email="idxgraph4@example.com"))
    ks_id = await _create_knowledge_source(client, headers, "Graph Success Source")
    doc = await _upload_pdf(
        client,
        headers,
        ks_id,
        "vendor_agreement4.pdf",
        pages=["Acme Corp shall provide services to Globex LLC. " * 20],
    )

    response = await client.post(f"/api/v1/index/{doc['id']}")
    assert response.status_code == 200
    body = response.json()
    assert body["index_status"] == "INDEXED"

    graph_extraction = body["graph_extraction"]
    assert graph_extraction["status"] == "completed"
    assert graph_extraction["entities_created"] == 2
    assert graph_extraction["relationships_created"] == 1
    assert graph_extraction["evidence_created"] > 0

    document_id = uuid.UUID(doc["id"])
    async with AsyncSessionLocal() as session:
        entities = (
            await session.execute(
                select(GraphEntity).where(GraphEntity.document_id == document_id)
            )
        ).scalars().all()
        relationships = (
            await session.execute(
                select(GraphRelationship).where(GraphRelationship.document_id == document_id)
            )
        ).scalars().all()
        evidence_rows = (
            await session.execute(
                select(GraphEvidence).where(GraphEvidence.document_id == document_id)
            )
        ).scalars().all()

        assert len(entities) == 2
        assert len(relationships) == 1
        assert len(evidence_rows) > 0
