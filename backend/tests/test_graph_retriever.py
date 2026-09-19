"""Tests for the Graph RAG retrieval foundation (Sprint 2):
GraphRetriever + its repository additions in graph_repository.py.

No LLM, no embeddings -- entities/relationships/evidence are built
directly via the ORM (no extraction pipeline involved), matching how
test_graph_extraction_service.py/test_graph_models.py already build
fixtures for this layer.
"""

import uuid

import pytest
from httpx import AsyncClient

from app.database.session import AsyncSessionLocal
from app.knowledge_engine.retrieval.graph_retriever import GraphRetriever
from app.models.graph import GraphEntity, GraphEvidence, GraphRelationship
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
    """Returns (document_id, knowledge_source_id). Creates a new
    knowledge source unless one is given (so multiple documents can
    share a knowledge source, for KS-scoped tests)."""
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


async def _make_entity(
    session, document_id: uuid.UUID, name: str, canonical_name: str, entity_type: str = "term"
) -> GraphEntity:
    entity = GraphEntity(
        document_id=document_id, name=name, canonical_name=canonical_name, entity_type=entity_type
    )
    session.add(entity)
    await session.flush()
    return entity


async def _make_relationship(
    session,
    document_id: uuid.UUID,
    source: GraphEntity,
    target: GraphEntity,
    relationship_type: str,
    *,
    confidence: float | None = 0.9,
) -> GraphRelationship:
    rel = GraphRelationship(
        document_id=document_id,
        source_entity_id=source.id,
        target_entity_id=target.id,
        relationship_type=relationship_type,
        confidence=confidence,
    )
    session.add(rel)
    await session.flush()
    return rel


async def _make_evidence(
    session,
    document_id: uuid.UUID,
    relationship: GraphRelationship,
    chunk_id: str,
    *,
    page_number: int | None = None,
    source_text: str | None = None,
) -> GraphEvidence:
    evidence = GraphEvidence(
        document_id=document_id,
        relationship_id=relationship.id,
        chunk_id=chunk_id,
        page_number=page_number,
        source_text=source_text,
    )
    session.add(evidence)
    await session.flush()
    return evidence


def _retriever(session) -> GraphRetriever:
    return GraphRetriever(
        GraphEntityRepository(session),
        GraphRelationshipRepository(session),
        GraphEvidenceRepository(session),
    )


# --- Entity matching ---------------------------------------------------


@pytest.mark.asyncio
async def test_entity_matching_finds_mentioned_entity(
    client: AsyncClient, register_and_login
) -> None:
    headers = _auth_headers(await register_and_login(email="graphret1@example.com"))
    document_id, ks_id = await _create_document(client, headers, "Fee Schedule")

    async with AsyncSessionLocal() as session:
        await _make_entity(session, document_id, "Registration Fees", "registration fees")
        await session.commit()

    async with AsyncSessionLocal() as session:
        result = await _retriever(session).retrieve(
            "What is the registration fees policy?", document_id=document_id
        )

    assert not result.is_empty
    assert len(result.matched_entities) == 1
    assert result.matched_entities[0].canonical_name == "registration fees"
    assert result.matched_entities[0].depth == 0


@pytest.mark.asyncio
async def test_empty_query_returns_empty_result(client: AsyncClient, register_and_login) -> None:
    headers = _auth_headers(await register_and_login(email="graphret2@example.com"))
    document_id, _ = await _create_document(client, headers, "Empty Query Doc")

    async with AsyncSessionLocal() as session:
        result = await _retriever(session).retrieve("   ", document_id=document_id)

    assert result.is_empty
    assert result.matched_entities == []
    assert result.relationships == []


@pytest.mark.asyncio
async def test_no_match_query_returns_empty_result(
    client: AsyncClient, register_and_login
) -> None:
    headers = _auth_headers(await register_and_login(email="graphret3@example.com"))
    document_id, _ = await _create_document(client, headers, "No Match Doc")

    async with AsyncSessionLocal() as session:
        await _make_entity(session, document_id, "Registration Fees", "registration fees")
        await session.commit()

    async with AsyncSessionLocal() as session:
        result = await _retriever(session).retrieve(
            "Tell me about the weather today", document_id=document_id
        )

    assert result.is_empty


# --- 1-hop and multi-hop traversal --------------------------------------


@pytest.mark.asyncio
async def test_one_hop_traversal_default_depth(client: AsyncClient, register_and_login) -> None:
    headers = _auth_headers(await register_and_login(email="graphret4@example.com"))
    document_id, _ = await _create_document(client, headers, "One Hop Doc")

    async with AsyncSessionLocal() as session:
        acme = await _make_entity(session, document_id, "Acme Corp", "acme corp", "organization")
        globex = await _make_entity(
            session, document_id, "Globex LLC", "globex llc", "organization"
        )
        await _make_relationship(session, document_id, acme, globex, "provides_services_to")
        await session.commit()

    async with AsyncSessionLocal() as session:
        result = await _retriever(session).retrieve("Tell me about Acme Corp", document_id=document_id)

    assert len(result.relationships) == 1
    rel = result.relationships[0]
    assert rel.relationship_type == "provides_services_to"
    assert rel.source.canonical_name == "acme corp"
    assert rel.target.canonical_name == "globex llc"
    assert rel.depth == 1
    assert rel.target.depth == 1  # reached via traversal, not a direct query match


@pytest.mark.asyncio
async def test_depth_zero_returns_no_relationships(
    client: AsyncClient, register_and_login
) -> None:
    headers = _auth_headers(await register_and_login(email="graphret5@example.com"))
    document_id, _ = await _create_document(client, headers, "Depth Zero Doc")

    async with AsyncSessionLocal() as session:
        acme = await _make_entity(session, document_id, "Acme Corp", "acme corp", "organization")
        globex = await _make_entity(
            session, document_id, "Globex LLC", "globex llc", "organization"
        )
        await _make_relationship(session, document_id, acme, globex, "provides_services_to")
        await session.commit()

    async with AsyncSessionLocal() as session:
        result = await _retriever(session).retrieve(
            "Tell me about Acme Corp", document_id=document_id, depth=0
        )

    assert len(result.matched_entities) == 1
    assert result.relationships == []


@pytest.mark.asyncio
async def test_multi_hop_traversal(client: AsyncClient, register_and_login) -> None:
    """Acme -> Globex -> Initech, depth=2 must reach Initech; depth=1 must not."""
    headers = _auth_headers(await register_and_login(email="graphret6@example.com"))
    document_id, _ = await _create_document(client, headers, "Multi Hop Doc")

    async with AsyncSessionLocal() as session:
        acme = await _make_entity(session, document_id, "Acme Corp", "acme corp", "organization")
        globex = await _make_entity(
            session, document_id, "Globex LLC", "globex llc", "organization"
        )
        initech = await _make_entity(
            session, document_id, "Initech", "initech", "organization"
        )
        await _make_relationship(session, document_id, acme, globex, "provides_services_to")
        await _make_relationship(session, document_id, globex, initech, "subcontracts_to")
        await session.commit()

    async with AsyncSessionLocal() as session:
        shallow = await _retriever(session).retrieve(
            "Tell me about Acme Corp", document_id=document_id, depth=1
        )
    async with AsyncSessionLocal() as session:
        deep = await _retriever(session).retrieve(
            "Tell me about Acme Corp", document_id=document_id, depth=2
        )

    shallow_entities = {e.canonical_name for e in shallow.entities}
    deep_entities = {e.canonical_name for e in deep.entities}

    assert "initech" not in shallow_entities
    assert len(shallow.relationships) == 1

    assert "initech" in deep_entities
    assert len(deep.relationships) == 2
    initech_match = next(e for e in deep.entities if e.canonical_name == "initech")
    assert initech_match.depth == 2


# --- Incoming and outgoing edges -----------------------------------------


@pytest.mark.asyncio
async def test_traversal_follows_both_incoming_and_outgoing_edges(
    client: AsyncClient, register_and_login
) -> None:
    """Globex is the TARGET of one edge (Acme->Globex) and the SOURCE
    of another (Globex->Initech) -- matching on Globex must surface
    both directions."""
    headers = _auth_headers(await register_and_login(email="graphret7@example.com"))
    document_id, _ = await _create_document(client, headers, "Bidirectional Doc")

    async with AsyncSessionLocal() as session:
        acme = await _make_entity(session, document_id, "Acme Corp", "acme corp", "organization")
        globex = await _make_entity(
            session, document_id, "Globex LLC", "globex llc", "organization"
        )
        initech = await _make_entity(
            session, document_id, "Initech", "initech", "organization"
        )
        await _make_relationship(session, document_id, acme, globex, "provides_services_to")
        await _make_relationship(session, document_id, globex, initech, "subcontracts_to")
        await session.commit()

    async with AsyncSessionLocal() as session:
        result = await _retriever(session).retrieve(
            "Tell me about Globex LLC", document_id=document_id
        )

    rel_types = {r.relationship_type for r in result.relationships}
    assert rel_types == {"provides_services_to", "subcontracts_to"}


# --- Document / knowledge-source scoping ---------------------------------


@pytest.mark.asyncio
async def test_document_scope_excludes_other_documents_in_same_knowledge_source(
    client: AsyncClient, register_and_login
) -> None:
    headers = _auth_headers(await register_and_login(email="graphret8@example.com"))
    doc_a, ks_id = await _create_document(client, headers, "Doc A")
    doc_b, _ = await _create_document(
        client, headers, "Doc B", knowledge_source_id=str(ks_id)
    )

    async with AsyncSessionLocal() as session:
        await _make_entity(session, doc_a, "Registration Fees", "registration fees")
        await _make_entity(session, doc_b, "Registration Fees", "registration fees")
        await session.commit()

    async with AsyncSessionLocal() as session:
        result = await _retriever(session).retrieve(
            "What is the registration fees policy?", document_id=doc_a
        )

    assert len(result.matched_entities) == 1
    assert result.matched_entities[0].entity_id is not None
    # Only doc_a's entity, not doc_b's -- confirmed via document scoping
    # rather than a coincidental single match, since both share the
    # same canonical_name.


@pytest.mark.asyncio
async def test_knowledge_source_scope_spans_its_documents_only(
    client: AsyncClient, register_and_login
) -> None:
    headers = _auth_headers(await register_and_login(email="graphret9@example.com"))
    doc_a, ks_id = await _create_document(client, headers, "KS Doc A")
    doc_b, _ = await _create_document(
        client, headers, "KS Doc B", knowledge_source_id=str(ks_id)
    )
    other_doc, other_ks_id = await _create_document(client, headers, "Other KS Doc")

    async with AsyncSessionLocal() as session:
        await _make_entity(session, doc_a, "Registration Fees", "registration fees")
        await _make_entity(session, doc_b, "Late Fee", "late fee")
        await _make_entity(session, other_doc, "Registration Fees", "registration fees")
        await session.commit()

    async with AsyncSessionLocal() as session:
        result = await _retriever(session).retrieve(
            "registration fees and late fee policy", knowledge_source_id=ks_id
        )

    matched_names = {e.canonical_name for e in result.matched_entities}
    # Both entities from ks_id's two documents, not the other KS's.
    assert matched_names == {"registration fees", "late fee"}


@pytest.mark.asyncio
async def test_retrieve_requires_a_scope() -> None:
    async with AsyncSessionLocal() as session:
        with pytest.raises(ValueError):
            await _retriever(session).retrieve("anything")


@pytest.mark.asyncio
async def test_malformed_relationship_does_not_leak_cross_document_entity(
    client: AsyncClient, register_and_login
) -> None:
    """A GraphRelationship's endpoints are not actually constrained
    (by FK or CHECK) to belong to the relationship's own document_id --
    normal extraction always keeps them consistent, but nothing in the
    schema enforces it. Construct exactly that inconsistent case
    directly and confirm traversal never surfaces the out-of-scope
    entity, rather than assuming the relationship's own document_id
    being in-scope is enough."""
    headers = _auth_headers(await register_and_login(email="graphret13@example.com"))
    doc_a, _ = await _create_document(client, headers, "Scope A Doc")
    doc_b, _ = await _create_document(client, headers, "Scope B Doc")

    async with AsyncSessionLocal() as session:
        acme = await _make_entity(session, doc_a, "Acme Corp", "acme corp", "organization")
        # Belongs to doc_b, not doc_a.
        secret = await _make_entity(
            session, doc_b, "Confidential Entity", "confidential entity", "organization"
        )
        # Malformed on purpose: this relationship's own document_id is
        # doc_a, but its target belongs to doc_b.
        rel = GraphRelationship(
            document_id=doc_a,
            source_entity_id=acme.id,
            target_entity_id=secret.id,
            relationship_type="linked_to",
        )
        session.add(rel)
        await session.commit()

    async with AsyncSessionLocal() as session:
        result = await _retriever(session).retrieve(
            "Tell me about Acme Corp", document_id=doc_a
        )

    entity_ids = {e.entity_id for e in result.entities}
    assert secret.id not in entity_ids
    # The malformed edge itself must not appear either -- not just the
    # entity hidden from view.
    assert all(r.relationship_id != rel.id for r in result.relationships)


# --- Cycle prevention ------------------------------------------------------


@pytest.mark.asyncio
async def test_cycle_does_not_cause_infinite_traversal_or_duplicates(
    client: AsyncClient, register_and_login
) -> None:
    """Acme -> Globex -> Acme (a real cycle) must terminate and must
    not return the same entity/relationship twice."""
    headers = _auth_headers(await register_and_login(email="graphret10@example.com"))
    document_id, _ = await _create_document(client, headers, "Cycle Doc")

    async with AsyncSessionLocal() as session:
        acme = await _make_entity(session, document_id, "Acme Corp", "acme corp", "organization")
        globex = await _make_entity(
            session, document_id, "Globex LLC", "globex llc", "organization"
        )
        await _make_relationship(session, document_id, acme, globex, "partners_with")
        await _make_relationship(session, document_id, globex, acme, "partners_with")
        await session.commit()

    async with AsyncSessionLocal() as session:
        result = await _retriever(session).retrieve(
            "Tell me about Acme Corp", document_id=document_id, depth=5, limit=50
        )

    relationship_ids = [r.relationship_id for r in result.relationships]
    assert len(relationship_ids) == len(set(relationship_ids))  # no duplicate edges
    entity_ids = [e.entity_id for e in result.entities]
    assert len(entity_ids) == len(set(entity_ids))  # no duplicate entities
    assert len(result.entities) == 2  # just Acme and Globex, traversal terminated


# --- Evidence / provenance -------------------------------------------------


@pytest.mark.asyncio
async def test_relationship_evidence_includes_chunk_page_and_source_text(
    client: AsyncClient, register_and_login
) -> None:
    headers = _auth_headers(await register_and_login(email="graphret11@example.com"))
    document_id, _ = await _create_document(client, headers, "Evidence Doc")

    async with AsyncSessionLocal() as session:
        acme = await _make_entity(session, document_id, "Acme Corp", "acme corp", "organization")
        globex = await _make_entity(
            session, document_id, "Globex LLC", "globex llc", "organization"
        )
        rel = await _make_relationship(session, document_id, acme, globex, "provides_services_to")
        await _make_evidence(
            session,
            document_id,
            rel,
            "node-0007",
            page_number=3,
            source_text="Acme Corp shall provide services to Globex LLC.",
        )
        await session.commit()

    async with AsyncSessionLocal() as session:
        result = await _retriever(session).retrieve("Tell me about Acme Corp", document_id=document_id)

    assert len(result.relationships) == 1
    evidence = result.relationships[0].evidence
    assert len(evidence) == 1
    assert evidence[0].chunk_id == "node-0007"
    assert evidence[0].page_number == 3
    assert evidence[0].source_text == "Acme Corp shall provide services to Globex LLC."


@pytest.mark.asyncio
async def test_relationship_with_no_evidence_returns_empty_evidence_list(
    client: AsyncClient, register_and_login
) -> None:
    headers = _auth_headers(await register_and_login(email="graphret12@example.com"))
    document_id, _ = await _create_document(client, headers, "No Evidence Doc")

    async with AsyncSessionLocal() as session:
        acme = await _make_entity(session, document_id, "Acme Corp", "acme corp", "organization")
        globex = await _make_entity(
            session, document_id, "Globex LLC", "globex llc", "organization"
        )
        await _make_relationship(session, document_id, acme, globex, "provides_services_to")
        await session.commit()

    async with AsyncSessionLocal() as session:
        result = await _retriever(session).retrieve("Tell me about Acme Corp", document_id=document_id)

    assert result.relationships[0].evidence == []
