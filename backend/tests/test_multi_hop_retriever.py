"""Tests for MultiHopRetriever (app/knowledge_engine/retrieval/multi_hop_retriever.py).

Same fixture-building pattern as test_graph_retriever.py: entities/
relationships/evidence built directly via the ORM, no extraction
pipeline, no LLM.
"""

import uuid

import pytest
from httpx import AsyncClient

from app.database.session import AsyncSessionLocal
from app.knowledge_engine.retrieval.graph_retriever import GraphRetriever
from app.knowledge_engine.retrieval.multi_hop_retriever import MultiHopRetriever
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
    if knowledge_source_id is None:
        ks_response = await client.post(KS_BASE, json={"name": f"{name} Source"}, headers=headers)
        knowledge_source_id = ks_response.json()["id"]
    doc_response = await client.post(
        DOC_BASE,
        json={"knowledge_source_id": knowledge_source_id, "name": name, "status": "indexed"},
        headers=headers,
    )
    return uuid.UUID(doc_response.json()["id"]), uuid.UUID(knowledge_source_id)


async def _make_entity(session, document_id, name, canonical_name, entity_type="organization"):
    entity = GraphEntity(
        document_id=document_id, name=name, canonical_name=canonical_name, entity_type=entity_type
    )
    session.add(entity)
    await session.flush()
    return entity


async def _make_relationship(session, document_id, source, target, relationship_type, *, confidence=0.9):
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


async def _make_evidence(session, document_id, relationship, chunk_id, *, page_number=None, source_text=None):
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


def _multi_hop(session, **kwargs) -> MultiHopRetriever:
    graph_retriever = GraphRetriever(
        GraphEntityRepository(session),
        GraphRelationshipRepository(session),
        GraphEvidenceRepository(session),
    )
    return MultiHopRetriever(graph_retriever, **kwargs)


async def _build_chain(session, document_id, names: list[str], relationship_type="leads_to"):
    """Builds a straight-line chain A -> B -> C -> ... and returns the
    list of created GraphEntity rows."""
    entities = [await _make_entity(session, document_id, n, n.lower()) for n in names]
    for a, b in zip(entities, entities[1:]):
        rel = await _make_relationship(session, document_id, a, b, relationship_type)
        await _make_evidence(
            session, document_id, rel, f"node-{a.canonical_name}-{b.canonical_name}",
            page_number=1, source_text=f"{a.name} {relationship_type} {b.name}.",
        )
    return entities


# --- One-hop / two-hop / depth capping / depth zero -------------------------


@pytest.mark.asyncio
async def test_one_hop_traversal(client: AsyncClient, register_and_login) -> None:
    headers = _auth_headers(await register_and_login(email="mh1@example.com"))
    document_id, _ = await _create_document(client, headers, "One Hop Doc")

    async with AsyncSessionLocal() as session:
        await _build_chain(session, document_id, ["Acme Corp", "Globex LLC", "Initech"])
        await session.commit()

    async with AsyncSessionLocal() as session:
        result = await _multi_hop(session).retrieve(
            "Tell me about Acme Corp", document_id=document_id, depth=1
        )

    assert result.depth_reached == 1
    entity_names = {e.canonical_name for e in result.entities}
    assert entity_names == {"acme corp", "globex llc"}
    assert "initech" not in entity_names


@pytest.mark.asyncio
async def test_two_hop_traversal_default_depth(client: AsyncClient, register_and_login) -> None:
    headers = _auth_headers(await register_and_login(email="mh2@example.com"))
    document_id, _ = await _create_document(client, headers, "Two Hop Doc")

    async with AsyncSessionLocal() as session:
        await _build_chain(session, document_id, ["Acme Corp", "Globex LLC", "Initech"])
        await session.commit()

    async with AsyncSessionLocal() as session:
        result = await _multi_hop(session).retrieve("Tell me about Acme Corp", document_id=document_id)

    assert result.depth_requested == 2  # default
    assert result.depth_reached == 2
    assert {e.canonical_name for e in result.entities} == {"acme corp", "globex llc", "initech"}
    path_with_two_steps = next(p for p in result.paths if p.depth == 2)
    assert path_with_two_steps.end_entity.canonical_name == "initech"


@pytest.mark.asyncio
async def test_three_hop_request_capped_by_configured_max_depth(
    client: AsyncClient, register_and_login
) -> None:
    headers = _auth_headers(await register_and_login(email="mh3@example.com"))
    document_id, _ = await _create_document(client, headers, "Capped Doc")

    async with AsyncSessionLocal() as session:
        await _build_chain(session, document_id, ["Node One", "Node Two", "Node Three", "Node Four"])
        await session.commit()

    async with AsyncSessionLocal() as session:
        result = await _multi_hop(session, max_depth=2).retrieve(
            "Tell me about Node One", document_id=document_id, depth=3
        )

    assert result.depth_requested == 3
    assert result.depth_reached == 2  # clamped
    assert "node four" not in {e.canonical_name for e in result.entities}
    assert all(p.depth <= 2 for p in result.paths)


@pytest.mark.asyncio
async def test_depth_zero_returns_seeds_only(client: AsyncClient, register_and_login) -> None:
    headers = _auth_headers(await register_and_login(email="mh4@example.com"))
    document_id, _ = await _create_document(client, headers, "Depth Zero Doc")

    async with AsyncSessionLocal() as session:
        await _build_chain(session, document_id, ["Acme Corp", "Globex LLC"])
        await session.commit()

    async with AsyncSessionLocal() as session:
        result = await _multi_hop(session).retrieve(
            "Tell me about Acme Corp", document_id=document_id, depth=0
        )

    assert len(result.seed_entities) == 1
    assert result.relationships == ()
    assert all(p.depth == 0 for p in result.paths)


# --- Multiple seeds / cycles / duplicate paths / incoming+outgoing ---------


@pytest.mark.asyncio
async def test_multiple_seed_entities(client: AsyncClient, register_and_login) -> None:
    headers = _auth_headers(await register_and_login(email="mh5@example.com"))
    document_id, _ = await _create_document(client, headers, "Multi Seed Doc")

    async with AsyncSessionLocal() as session:
        acme = await _make_entity(session, document_id, "Acme Corp", "acme corp")
        globex = await _make_entity(session, document_id, "Globex LLC", "globex llc")
        rel = await _make_relationship(session, document_id, acme, globex, "partners_with")
        await _make_evidence(session, document_id, rel, "node-1")
        await session.commit()

    async with AsyncSessionLocal() as session:
        result = await _multi_hop(session).retrieve(
            "Acme Corp and Globex LLC", document_id=document_id, depth=0
        )

    assert len(result.seed_entities) == 2


@pytest.mark.asyncio
async def test_cycle_protection(client: AsyncClient, register_and_login) -> None:
    headers = _auth_headers(await register_and_login(email="mh6@example.com"))
    document_id, _ = await _create_document(client, headers, "Cycle Doc")

    async with AsyncSessionLocal() as session:
        acme = await _make_entity(session, document_id, "Acme Corp", "acme corp")
        globex = await _make_entity(session, document_id, "Globex LLC", "globex llc")
        await _make_relationship(session, document_id, acme, globex, "partners_with")
        await _make_relationship(session, document_id, globex, acme, "partners_with")
        await session.commit()

    async with AsyncSessionLocal() as session:
        result = await _multi_hop(session, max_depth=5).retrieve(
            "Tell me about Acme Corp", document_id=document_id
        )

    assert len(result.entities) == 2  # no runaway growth
    for path in result.paths:
        visited = [path.seed_entity.entity_id] + [s.target_entity.entity_id for s in path.steps]
        assert len(visited) == len(set(visited))  # no entity revisited within a path


@pytest.mark.asyncio
async def test_duplicate_paths_are_deduplicated(client: AsyncClient, register_and_login) -> None:
    """Two independent 2-hop routes to the SAME end entity must not
    collapse into one path (they're genuinely different reasoning
    chains) -- but re-running retrieve() must not multiply the count."""
    headers = _auth_headers(await register_and_login(email="mh7@example.com"))
    document_id, _ = await _create_document(client, headers, "Diamond Doc")

    async with AsyncSessionLocal() as session:
        a = await _make_entity(session, document_id, "Node A", "node a")
        b = await _make_entity(session, document_id, "Node B", "node b")
        c = await _make_entity(session, document_id, "Node C", "node c")
        d = await _make_entity(session, document_id, "Node D", "node d")
        await _make_relationship(session, document_id, a, b, "leads_to")
        await _make_relationship(session, document_id, a, c, "leads_to")
        await _make_relationship(session, document_id, b, d, "leads_to")
        await _make_relationship(session, document_id, c, d, "leads_to")
        await session.commit()

    async with AsyncSessionLocal() as session:
        result = await _multi_hop(session, max_depth=2).retrieve(
            "Tell me about Node A", document_id=document_id
        )

    two_hop_paths_to_d = [
        p for p in result.paths if p.depth == 2 and p.end_entity.canonical_name == "node d"
    ]
    assert len(two_hop_paths_to_d) == 2  # via B and via C -- both genuine, neither duplicated


@pytest.mark.asyncio
async def test_incoming_and_outgoing_relationships_both_followed(
    client: AsyncClient, register_and_login
) -> None:
    headers = _auth_headers(await register_and_login(email="mh8@example.com"))
    document_id, _ = await _create_document(client, headers, "Bidirectional Doc")

    async with AsyncSessionLocal() as session:
        acme = await _make_entity(session, document_id, "Acme Corp", "acme corp")
        globex = await _make_entity(session, document_id, "Globex LLC", "globex llc")
        initech = await _make_entity(session, document_id, "Initech", "initech")
        await _make_relationship(session, document_id, acme, globex, "provides_services_to")
        await _make_relationship(session, document_id, globex, initech, "subcontracts_to")
        await session.commit()

    async with AsyncSessionLocal() as session:
        result = await _multi_hop(session).retrieve(
            "Tell me about Globex LLC", document_id=document_id
        )

    rel_types = {r.relationship_type for r in result.relationships}
    assert rel_types == {"provides_services_to", "subcontracts_to"}


# --- Scope isolation ---------------------------------------------------------


@pytest.mark.asyncio
async def test_document_scope_isolation(client: AsyncClient, register_and_login) -> None:
    headers = _auth_headers(await register_and_login(email="mh9@example.com"))
    doc_a, ks_id = await _create_document(client, headers, "Scope Doc A")
    doc_b, _ = await _create_document(client, headers, "Scope Doc B", knowledge_source_id=str(ks_id))

    async with AsyncSessionLocal() as session:
        await _make_entity(session, doc_a, "Registration Fees", "registration fees")
        await _make_entity(session, doc_b, "Registration Fees", "registration fees")
        await session.commit()

    async with AsyncSessionLocal() as session:
        result = await _multi_hop(session).retrieve("registration fees", document_id=doc_a, depth=0)

    assert len(result.seed_entities) == 1


@pytest.mark.asyncio
async def test_knowledge_source_scope_isolation(client: AsyncClient, register_and_login) -> None:
    headers = _auth_headers(await register_and_login(email="mh10@example.com"))
    doc_a, ks_id = await _create_document(client, headers, "KS Doc A")
    other_doc, _ = await _create_document(client, headers, "Other KS Doc")

    async with AsyncSessionLocal() as session:
        await _make_entity(session, doc_a, "Registration Fees", "registration fees")
        await _make_entity(session, other_doc, "Registration Fees", "registration fees")
        await session.commit()

    async with AsyncSessionLocal() as session:
        result = await _multi_hop(session).retrieve(
            "registration fees", knowledge_source_id=ks_id, depth=0
        )

    assert len(result.seed_entities) == 1


@pytest.mark.asyncio
async def test_malformed_cross_document_relationship_isolation(
    client: AsyncClient, register_and_login
) -> None:
    """A relationship whose own document_id is in-scope but whose
    endpoint belongs to a different document must not leak that
    endpoint -- same guarantee GraphRetriever itself provides,
    inherited unmodified here."""
    headers = _auth_headers(await register_and_login(email="mh11@example.com"))
    doc_a, _ = await _create_document(client, headers, "Malformed A")
    doc_b, _ = await _create_document(client, headers, "Malformed B")

    async with AsyncSessionLocal() as session:
        acme = await _make_entity(session, doc_a, "Acme Corp", "acme corp")
        secret = await _make_entity(session, doc_b, "Confidential Entity", "confidential entity")
        rel = GraphRelationship(
            document_id=doc_a,
            source_entity_id=acme.id,
            target_entity_id=secret.id,
            relationship_type="linked_to",
        )
        session.add(rel)
        await session.commit()

    async with AsyncSessionLocal() as session:
        result = await _multi_hop(session).retrieve("Tell me about Acme Corp", document_id=doc_a)

    entity_ids = {e.entity_id for e in result.entities}
    assert secret.id not in entity_ids


# --- Evidence provenance / ordering / limits / empty ------------------------


@pytest.mark.asyncio
async def test_evidence_provenance_preservation(client: AsyncClient, register_and_login) -> None:
    headers = _auth_headers(await register_and_login(email="mh12@example.com"))
    document_id, _ = await _create_document(client, headers, "Provenance Doc")

    async with AsyncSessionLocal() as session:
        acme = await _make_entity(session, document_id, "Acme Corp", "acme corp")
        globex = await _make_entity(session, document_id, "Globex LLC", "globex llc")
        rel = await _make_relationship(
            session, document_id, acme, globex, "provides_services_to", confidence=0.77
        )
        await _make_evidence(
            session, document_id, rel, "node-0007", page_number=3,
            source_text="Acme Corp shall provide services to Globex LLC.",
        )
        await session.commit()

    async with AsyncSessionLocal() as session:
        result = await _multi_hop(session).retrieve("Tell me about Acme Corp", document_id=document_id)

    assert len(result.evidence) == 1
    ev = result.evidence[0]
    assert ev.chunk_id == "node-0007"
    assert ev.page_number == 3
    assert ev.source_text == "Acme Corp shall provide services to Globex LLC."
    assert ev.relationship_type == "provides_services_to"
    assert ev.source_entity.canonical_name == "acme corp"
    assert ev.target_entity.canonical_name == "globex llc"
    assert ev.depth == 1
    assert ev.confidence == pytest.approx(0.77)


@pytest.mark.asyncio
async def test_deterministic_ordering_across_repeated_calls(
    client: AsyncClient, register_and_login
) -> None:
    headers = _auth_headers(await register_and_login(email="mh13@example.com"))
    document_id, _ = await _create_document(client, headers, "Deterministic Doc")

    async with AsyncSessionLocal() as session:
        await _build_chain(session, document_id, ["Acme Corp", "Globex LLC", "Initech"])
        await session.commit()

    async with AsyncSessionLocal() as session:
        first = await _multi_hop(session).retrieve("Tell me about Acme Corp", document_id=document_id)
    async with AsyncSessionLocal() as session:
        second = await _multi_hop(session).retrieve("Tell me about Acme Corp", document_id=document_id)

    assert [e.entity_id for e in first.entities] == [e.entity_id for e in second.entities]
    assert [r.relationship_id for r in first.relationships] == [
        r.relationship_id for r in second.relationships
    ]
    assert [ev.chunk_id for ev in first.evidence] == [ev.chunk_id for ev in second.evidence]
    assert [(p.seed_entity.entity_id, p.depth) for p in first.paths] == [
        (p.seed_entity.entity_id, p.depth) for p in second.paths
    ]


@pytest.mark.asyncio
async def test_traversal_limits_are_enforced(client: AsyncClient, register_and_login) -> None:
    headers = _auth_headers(await register_and_login(email="mh14@example.com"))
    document_id, _ = await _create_document(client, headers, "Limits Doc")

    async with AsyncSessionLocal() as session:
        hub = await _make_entity(session, document_id, "Hub", "hub")
        for i in range(10):
            leaf = await _make_entity(session, document_id, f"Leaf {i}", f"leaf {i}")
            rel = await _make_relationship(session, document_id, hub, leaf, "connects_to")
            await _make_evidence(session, document_id, rel, f"node-{i}")
        await session.commit()

    async with AsyncSessionLocal() as session:
        result = await _multi_hop(session, max_relationships=3, max_evidence_items=3).retrieve(
            "Tell me about Hub", document_id=document_id
        )

    assert len(result.relationships) <= 3
    assert len(result.evidence) <= 3


@pytest.mark.asyncio
async def test_max_seed_entities_bounds_final_result_not_just_seed_list(
    client: AsyncClient, register_and_login
) -> None:
    """Regression test: max_seed_entities must bound what's actually
    REACHABLE in the final result, not just truncate the seed_entities
    list while leaving relationships/entities/evidence discovered from
    a discarded seed in place. Two independent seeds each match the
    query; max_seed_entities=1 keeps only "acme corp" (alphabetically
    first) -- "fabrikam" (only reachable from the discarded
    "northwind traders" seed) must not appear anywhere in the result.
    """
    headers = _auth_headers(await register_and_login(email="mh17@example.com"))
    document_id, _ = await _create_document(client, headers, "Seed Bound Doc")

    async with AsyncSessionLocal() as session:
        acme = await _make_entity(session, document_id, "Acme Corp", "acme corp")
        globex = await _make_entity(session, document_id, "Globex LLC", "globex llc")
        acme_rel = await _make_relationship(session, document_id, acme, globex, "partners_with")
        await _make_evidence(session, document_id, acme_rel, "node-acme-globex")

        northwind = await _make_entity(session, document_id, "Northwind Traders", "northwind traders")
        fabrikam = await _make_entity(session, document_id, "Fabrikam Inc", "fabrikam inc")
        northwind_rel = await _make_relationship(
            session, document_id, northwind, fabrikam, "partners_with"
        )
        await _make_evidence(session, document_id, northwind_rel, "node-northwind-fabrikam")
        await session.commit()

    async with AsyncSessionLocal() as session:
        result = await _multi_hop(session, max_seed_entities=1).retrieve(
            "Acme Corp and Northwind Traders", document_id=document_id
        )

    assert len(result.seed_entities) == 1
    assert result.seed_entities[0].canonical_name == "acme corp"  # alphabetically first, retained

    entity_names = {e.canonical_name for e in result.entities}
    assert "globex llc" in entity_names  # reachable from the retained seed
    assert "northwind traders" not in entity_names  # the discarded seed itself
    assert "fabrikam inc" not in entity_names  # only reachable via the discarded seed

    relationship_types_sources = {(r.relationship_type, r.source.canonical_name) for r in result.relationships}
    assert ("partners_with", "acme corp") in relationship_types_sources
    assert northwind_rel.id not in {r.relationship_id for r in result.relationships}

    evidence_chunk_ids = {ev.chunk_id for ev in result.evidence}
    assert "node-acme-globex" in evidence_chunk_ids
    assert "node-northwind-fabrikam" not in evidence_chunk_ids

    assert all(p.seed_entity.canonical_name == "acme corp" for p in result.paths)


@pytest.mark.asyncio
async def test_empty_query_returns_empty_result(client: AsyncClient, register_and_login) -> None:
    headers = _auth_headers(await register_and_login(email="mh15@example.com"))
    document_id, _ = await _create_document(client, headers, "Empty Query Doc")

    async with AsyncSessionLocal() as session:
        result = await _multi_hop(session).retrieve("   ", document_id=document_id)

    assert result.is_empty
    assert result.seed_entities == ()
    assert result.paths == ()


@pytest.mark.asyncio
async def test_no_entity_match_returns_empty_result(client: AsyncClient, register_and_login) -> None:
    headers = _auth_headers(await register_and_login(email="mh16@example.com"))
    document_id, _ = await _create_document(client, headers, "No Match Doc")

    async with AsyncSessionLocal() as session:
        await _make_entity(session, document_id, "Acme Corp", "acme corp")
        await session.commit()

    async with AsyncSessionLocal() as session:
        result = await _multi_hop(session).retrieve(
            "totally unrelated weather forecast", document_id=document_id
        )

    assert result.is_empty
