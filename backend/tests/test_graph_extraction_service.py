"""Tests for the Graph RAG extraction/persistence layer.

Covers entity extraction, relationship extraction, entity resolution
(dedup across chunks), relationship persistence, provenance, rerun
idempotency, and malformed-LLM-output isolation -- per the Graph RAG
extraction service spec. No real LLM call is made: the LLM gateway is
replaced with a fake that returns preset JSON strings, following the
same pattern as ``tests/test_response_quality_gate.py``.

This does not touch Qdrant, retrieval, chunking, chat orchestration, or
answer generation -- it only exercises the new extraction/persistence
code against HierarchicalChunk objects built directly in the test.
"""

import uuid
from types import SimpleNamespace

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.database.session import AsyncSessionLocal
from app.knowledge_engine.graph.extractor import GraphExtractionError, GraphExtractor
from app.knowledge_engine.graph.graph_extraction_service import GraphExtractionService
from app.knowledge_engine.models import ChunkMetadata, HierarchicalChunk
from app.models.graph import GraphEntity, GraphEvidence, GraphRelationship

KS_BASE = "/api/v1/knowledge-sources"
DOC_BASE = "/api/v1/documents"


def _auth_headers(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _create_document(client: AsyncClient, headers: dict, name: str) -> uuid.UUID:
    ks_response = await client.post(KS_BASE, json={"name": f"{name} Source"}, headers=headers)
    ks_id = ks_response.json()["id"]

    doc_response = await client.post(
        DOC_BASE,
        json={"knowledge_source_id": ks_id, "name": name, "status": "indexed"},
        headers=headers,
    )
    return uuid.UUID(doc_response.json()["id"])


def _chunk(document_id: uuid.UUID, node_id: str, text: str, *, page_number: int | None = None):
    return HierarchicalChunk(
        text=text,
        metadata=ChunkMetadata(
            document_id=str(document_id),
            knowledge_source_id=str(uuid.uuid4()),
            document_name="Vendor Services Agreement.pdf",
            chunk_number=0,
            page_number=page_number,
        ),
        node_id=node_id,
    )


class _FakeGateway:
    """Returns one preset raw response string per call, in order."""

    def __init__(self, responses: list[str]):
        self.responses = iter(responses)
        self.requests: list = []

    async def generate(self, request):
        self.requests.append(request)
        return SimpleNamespace(content=next(self.responses))


_ACME_GLOBEX_JSON = """{
  "entities": [
    {"name": "Acme Corp", "canonical_name": "acme corp", "entity_type": "organization"},
    {"name": "Globex LLC", "canonical_name": "globex llc", "entity_type": "organization"}
  ],
  "relationships": [
    {"source_entity": "acme corp", "target_entity": "globex llc", \
"relationship_type": "provides_services_to", "confidence": 0.92}
  ]
}"""

_EMPTY_JSON = '{"entities": [], "relationships": []}'


# --- 1. Entity extraction --------------------------------------------------


@pytest.mark.asyncio
async def test_extractor_parses_entities() -> None:
    gateway = _FakeGateway([_ACME_GLOBEX_JSON])
    extractor = GraphExtractor(gateway)

    result = await extractor.extract("Acme Corp shall provide services to Globex LLC.")

    assert {(e.name, e.canonical_name, e.entity_type) for e in result.entities} == {
        ("Acme Corp", "acme corp", "organization"),
        ("Globex LLC", "globex llc", "organization"),
    }


# --- 2. Relationship extraction ---------------------------------------------


@pytest.mark.asyncio
async def test_extractor_parses_relationships() -> None:
    gateway = _FakeGateway([_ACME_GLOBEX_JSON])
    extractor = GraphExtractor(gateway)

    result = await extractor.extract("Acme Corp shall provide services to Globex LLC.")

    assert len(result.relationships) == 1
    rel = result.relationships[0]
    assert rel.source_entity == "acme corp"
    assert rel.target_entity == "globex llc"
    assert rel.relationship_type == "provides_services_to"
    assert rel.confidence == pytest.approx(0.92)


@pytest.mark.asyncio
async def test_extractor_drops_relationship_referencing_unknown_entity() -> None:
    """A relationship whose source/target isn't in this chunk's own
    entities list is dropped rather than persisted with a dangling
    reference -- covers malformed-but-JSON-valid LLM output."""
    gateway = _FakeGateway(
        [
            """{
              "entities": [
                {"name": "Acme Corp", "canonical_name": "acme corp", "entity_type": "organization"}
              ],
              "relationships": [
                {"source_entity": "acme corp", "target_entity": "nonexistent entity", \
"relationship_type": "provides_services_to", "confidence": 0.9}
              ]
            }"""
        ]
    )
    extractor = GraphExtractor(gateway)

    result = await extractor.extract("Acme Corp shall provide services to someone.")

    assert result.entities[0].canonical_name == "acme corp"
    assert result.relationships == []


# --- Malformed LLM output ----------------------------------------------------


@pytest.mark.asyncio
async def test_extractor_raises_on_invalid_json() -> None:
    gateway = _FakeGateway(["this is not json at all"])
    extractor = GraphExtractor(gateway)

    with pytest.raises(GraphExtractionError):
        await extractor.extract("some chunk text")


@pytest.mark.asyncio
async def test_extractor_tolerates_missing_optional_keys() -> None:
    """Valid JSON that's just missing entities/relationships (both
    optional, defaulting to []) is not an error -- only genuinely
    malformed shapes should raise."""
    gateway = _FakeGateway(['{"foo": "bar"}'])
    extractor = GraphExtractor(gateway)

    result = await extractor.extract("some chunk text")
    assert result.entities == []
    assert result.relationships == []


@pytest.mark.asyncio
async def test_extractor_raises_on_valid_json_wrong_shape() -> None:
    """Valid JSON whose fields don't match the expected schema (here,
    "entities" is a string instead of a list) is a schema mismatch, not
    a JSON syntax error -- both must raise the same
    GraphExtractionError so the service can isolate either kind."""
    gateway = _FakeGateway(['{"entities": "not a list", "relationships": []}'])
    extractor = GraphExtractor(gateway)

    with pytest.raises(GraphExtractionError):
        await extractor.extract("some chunk text")


@pytest.mark.asyncio
async def test_extractor_strips_markdown_json_fences() -> None:
    fenced = f"```json\n{_ACME_GLOBEX_JSON}\n```"
    gateway = _FakeGateway([fenced])
    extractor = GraphExtractor(gateway)

    result = await extractor.extract("Acme Corp shall provide services to Globex LLC.")

    assert len(result.entities) == 2


# --- Service-level tests (extraction + persistence) -------------------------


@pytest.mark.asyncio
async def test_entity_resolution_dedups_across_chunks(
    client: AsyncClient, register_and_login
) -> None:
    """The same entity mentioned in two different chunks of the same
    document must resolve to a single GraphEntity row, not two."""
    headers = _auth_headers(await register_and_login(email="graphsvc1@example.com"))
    document_id = await _create_document(client, headers, "Vendor Services Agreement A")

    chunks = [
        _chunk(document_id, "node-0001", "Acme Corp shall provide services to Globex LLC."),
        _chunk(
            document_id,
            "node-0002",
            "Acme Corp shall provide services to Globex LLC. (recap clause)",
        ),
    ]
    gateway = _FakeGateway([_ACME_GLOBEX_JSON, _ACME_GLOBEX_JSON])
    extractor = GraphExtractor(gateway)

    async with AsyncSessionLocal() as session:
        service = GraphExtractionService(session, extractor)
        result = await service.extract_for_document(document_id, chunks)

    assert result.chunks_succeeded == 2
    assert result.chunks_failed == 0
    # Two entities total (Acme Corp, Globex LLC) -- NOT four, even
    # though both chunks extracted both entities.
    assert result.entities_created == 2
    # One relationship, reused across both chunks.
    assert result.relationships_created == 1
    # Two evidence rows: same relationship, but two distinct chunks.
    assert result.evidence_created == 2

    async with AsyncSessionLocal() as session:
        entities = (
            await session.execute(
                select(GraphEntity).where(GraphEntity.document_id == document_id)
            )
        ).scalars().all()
        assert len(entities) == 2


# --- 4. Relationship persistence --------------------------------------------


@pytest.mark.asyncio
async def test_relationship_persisted_with_correct_entities_and_confidence(
    client: AsyncClient, register_and_login
) -> None:
    headers = _auth_headers(await register_and_login(email="graphsvc2@example.com"))
    document_id = await _create_document(client, headers, "Vendor Services Agreement B")

    chunks = [_chunk(document_id, "node-0001", "Acme Corp shall provide services to Globex LLC.")]
    gateway = _FakeGateway([_ACME_GLOBEX_JSON])
    extractor = GraphExtractor(gateway)

    async with AsyncSessionLocal() as session:
        service = GraphExtractionService(session, extractor)
        await service.extract_for_document(document_id, chunks)

    async with AsyncSessionLocal() as session:
        relationship = (
            await session.execute(
                select(GraphRelationship).where(GraphRelationship.document_id == document_id)
            )
        ).scalar_one()
        assert relationship.relationship_type == "provides_services_to"
        assert relationship.confidence == pytest.approx(0.92)

        source = await session.get(GraphEntity, relationship.source_entity_id)
        target = await session.get(GraphEntity, relationship.target_entity_id)
        assert source.canonical_name == "acme corp"
        assert target.canonical_name == "globex llc"


# --- 5. Provenance -----------------------------------------------------------


@pytest.mark.asyncio
async def test_evidence_records_full_provenance(
    client: AsyncClient, register_and_login
) -> None:
    headers = _auth_headers(await register_and_login(email="graphsvc3@example.com"))
    document_id = await _create_document(client, headers, "Vendor Services Agreement C")

    chunk_text = "Acme Corp shall provide services to Globex LLC."
    chunks = [_chunk(document_id, "node-0007", chunk_text, page_number=3)]
    gateway = _FakeGateway([_ACME_GLOBEX_JSON])
    extractor = GraphExtractor(gateway)

    async with AsyncSessionLocal() as session:
        service = GraphExtractionService(session, extractor)
        await service.extract_for_document(document_id, chunks)

    async with AsyncSessionLocal() as session:
        evidence = (
            await session.execute(
                select(GraphEvidence).where(GraphEvidence.document_id == document_id)
            )
        ).scalar_one()
        assert evidence.chunk_id == "node-0007"
        assert evidence.page_number == 3
        assert evidence.source_text == chunk_text

        relationship = await session.get(GraphRelationship, evidence.relationship_id)
        assert relationship is not None
        assert relationship.document_id == document_id


# --- 6. Rerunning the same chunks without duplicates ------------------------


@pytest.mark.asyncio
async def test_rerunning_extraction_for_same_document_creates_no_duplicates(
    client: AsyncClient, register_and_login
) -> None:
    headers = _auth_headers(await register_and_login(email="graphsvc4@example.com"))
    document_id = await _create_document(client, headers, "Vendor Services Agreement D")

    chunks = [_chunk(document_id, "node-0001", "Acme Corp shall provide services to Globex LLC.")]

    # First run.
    gateway1 = _FakeGateway([_ACME_GLOBEX_JSON])
    async with AsyncSessionLocal() as session:
        service = GraphExtractionService(session, GraphExtractor(gateway1))
        first = await service.extract_for_document(document_id, chunks)

    assert first.entities_created == 2
    assert first.relationships_created == 1
    assert first.evidence_created == 1

    # Second run: identical document_id, identical chunks (simulating a
    # document re-index), identical LLM output.
    gateway2 = _FakeGateway([_ACME_GLOBEX_JSON])
    async with AsyncSessionLocal() as session:
        service = GraphExtractionService(session, GraphExtractor(gateway2))
        second = await service.extract_for_document(document_id, chunks)

    assert second.chunks_succeeded == 1
    assert second.entities_created == 0
    assert second.relationships_created == 0
    assert second.evidence_created == 0

    async with AsyncSessionLocal() as session:
        entity_count = len(
            (
                await session.execute(
                    select(GraphEntity).where(GraphEntity.document_id == document_id)
                )
            )
            .scalars()
            .all()
        )
        relationship_count = len(
            (
                await session.execute(
                    select(GraphRelationship).where(GraphRelationship.document_id == document_id)
                )
            )
            .scalars()
            .all()
        )
        evidence_count = len(
            (
                await session.execute(
                    select(GraphEvidence).where(GraphEvidence.document_id == document_id)
                )
            )
            .scalars()
            .all()
        )
        assert entity_count == 2
        assert relationship_count == 1
        assert evidence_count == 1


# --- 7. Malformed LLM output isolation ---------------------------------------


@pytest.mark.asyncio
async def test_malformed_chunk_is_isolated_and_does_not_block_other_chunks(
    client: AsyncClient, register_and_login
) -> None:
    headers = _auth_headers(await register_and_login(email="graphsvc5@example.com"))
    document_id = await _create_document(client, headers, "Vendor Services Agreement E")

    chunks = [
        _chunk(document_id, "node-0001", "Acme Corp shall provide services to Globex LLC."),
        _chunk(document_id, "node-0002", "This chunk will get garbage LLM output."),
        _chunk(document_id, "node-0003", "A second good chunk, re-mentioning Acme Corp."),
    ]
    gateway = _FakeGateway(
        [
            _ACME_GLOBEX_JSON,
            "not valid json {{{",
            _ACME_GLOBEX_JSON,
        ]
    )
    extractor = GraphExtractor(gateway)

    async with AsyncSessionLocal() as session:
        service = GraphExtractionService(session, extractor)
        result = await service.extract_for_document(document_id, chunks)

    assert result.chunks_processed == 3
    assert result.chunks_succeeded == 2
    assert result.chunks_failed == 1
    assert len(result.errors) == 1
    assert result.errors[0].chunk_id == "node-0002"

    # The two good chunks still produced persisted data despite the
    # bad chunk in between.
    async with AsyncSessionLocal() as session:
        evidence_rows = (
            await session.execute(
                select(GraphEvidence).where(GraphEvidence.document_id == document_id)
            )
        ).scalars().all()
        assert {row.chunk_id for row in evidence_rows} == {"node-0001", "node-0003"}


@pytest.mark.asyncio
async def test_all_chunks_empty_extraction_creates_nothing(
    client: AsyncClient, register_and_login
) -> None:
    headers = _auth_headers(await register_and_login(email="graphsvc6@example.com"))
    document_id = await _create_document(client, headers, "Vendor Services Agreement F")

    chunks = [_chunk(document_id, "node-0001", "This paragraph has no notable entities.")]
    gateway = _FakeGateway([_EMPTY_JSON])
    extractor = GraphExtractor(gateway)

    async with AsyncSessionLocal() as session:
        service = GraphExtractionService(session, extractor)
        result = await service.extract_for_document(document_id, chunks)

    assert result.chunks_succeeded == 1
    assert result.entities_created == 0
    assert result.relationships_created == 0
    assert result.evidence_created == 0


# --- Regression: rollback must not leave stale entities in the cache -------


@pytest.mark.asyncio
async def test_failed_chunk_does_not_leave_stale_entity_in_shared_cache(
    client: AsyncClient, register_and_login
) -> None:
    """chunk1 creates entities, then fails during relationship
    persistence (simulated DB error) and must roll back completely.
    chunk2, in the same ``extract_for_document`` call, references the
    same entities and must re-resolve/re-create them fresh -- not
    reuse the stale, rolled-back ORM objects from chunk1's cache
    entry. Under the pre-fix implementation this would cause chunk2 to
    also fail (a ForeignKeyViolation inserting a relationship against
    entity ids that were rolled back), which is exactly what this test
    guards against.
    """
    headers = _auth_headers(await register_and_login(email="graphsvc7@example.com"))
    document_id = await _create_document(client, headers, "Vendor Services Agreement G")

    chunk1 = _chunk(document_id, "node-0001", "Acme Corp shall provide services to Globex LLC.")
    chunk2 = _chunk(
        document_id,
        "node-0002",
        "Acme Corp shall provide services to Globex LLC. (recap clause)",
    )

    gateway = _FakeGateway([_ACME_GLOBEX_JSON, _ACME_GLOBEX_JSON])
    extractor = GraphExtractor(gateway)

    async with AsyncSessionLocal() as session:
        service = GraphExtractionService(session, extractor)

        # Force the relationship-persistence step to fail on its FIRST
        # call only -- i.e. after chunk1's entities have already been
        # created (and would, pre-fix, have been written into the
        # shared entity_cache) but before chunk1 commits.
        original_create = service.relationships.create
        call_count = {"n": 0}

        async def flaky_create(obj):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise RuntimeError("simulated DB failure after entity creation")
            return await original_create(obj)

        service.relationships.create = flaky_create

        result = await service.extract_for_document(document_id, [chunk1, chunk2])

    assert result.chunks_processed == 2
    assert result.chunks_failed == 1
    assert result.chunks_succeeded == 1
    assert result.errors[0].chunk_id == "node-0001"

    # chunk1 contributed nothing (fully rolled back); chunk2 correctly
    # created everything fresh on its own.
    assert result.entities_created == 2
    assert result.relationships_created == 1
    assert result.evidence_created == 1

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
        assert len(evidence_rows) == 1
        assert evidence_rows[0].chunk_id == "node-0002"


# --- Regression: evidence cannot cross document boundaries -----------------


@pytest.mark.asyncio
async def test_evidence_cannot_reference_relationship_from_different_document(
    client: AsyncClient, register_and_login
) -> None:
    """A GraphEvidence row must not be able to attach a
    document-B document_id to a relationship that actually belongs to
    document A -- enforced by the composite FK on
    (relationship_id, document_id) -> graph_relationships(id, document_id).
    """
    headers = _auth_headers(await register_and_login(email="graphsvc8@example.com"))
    document_a = await _create_document(client, headers, "Vendor Services Agreement H")
    document_b = await _create_document(client, headers, "Vendor Services Agreement I")

    chunks = [_chunk(document_a, "node-0001", "Acme Corp shall provide services to Globex LLC.")]
    gateway = _FakeGateway([_ACME_GLOBEX_JSON])
    extractor = GraphExtractor(gateway)

    async with AsyncSessionLocal() as session:
        service = GraphExtractionService(session, extractor)
        await service.extract_for_document(document_a, chunks)

    async with AsyncSessionLocal() as session:
        relationship = (
            await session.execute(
                select(GraphRelationship).where(GraphRelationship.document_id == document_a)
            )
        ).scalar_one()

        session.add(
            GraphEvidence(
                relationship_id=relationship.id,
                document_id=document_b,  # mismatched on purpose
                chunk_id="node-9999",
                source_text="forged cross-document evidence",
            )
        )
        with pytest.raises(IntegrityError):
            await session.commit()
