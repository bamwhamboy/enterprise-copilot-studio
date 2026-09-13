"""Tests for the Graph RAG persistence layer (Sprint: Graph RAG).

Covers the three tables added for the knowledge graph
(GraphEntity/GraphRelationship/GraphEvidence): basic persistence,
provenance traversal, cascade deletes from Document, and the
duplicate-prevention constraints that keep re-indexing idempotent.

These tests only exercise the persistence layer -- they do not touch
Qdrant, retrieval, or the existing hybrid RAG pipeline.
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.database.session import AsyncSessionLocal
from app.models import Document, GraphEntity, GraphEvidence, GraphRelationship

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


@pytest.mark.asyncio
async def test_create_entity_relationship_and_evidence(
    client: AsyncClient, register_and_login
) -> None:
    headers = _auth_headers(await register_and_login(email="graph1@example.com"))
    document_id = await _create_document(client, headers, "Vendor Services Agreement A")

    async with AsyncSessionLocal() as session:
        vendor = GraphEntity(
            document_id=document_id,
            name="Acme Corp",
            canonical_name="acme corp",
            entity_type="organization",
        )
        client_party = GraphEntity(
            document_id=document_id,
            name="Globex LLC",
            canonical_name="globex llc",
            entity_type="organization",
        )
        session.add_all([vendor, client_party])
        await session.flush()

        relationship = GraphRelationship(
            document_id=document_id,
            source_entity_id=vendor.id,
            target_entity_id=client_party.id,
            relationship_type="provides_services_to",
            confidence=0.92,
        )
        session.add(relationship)
        await session.flush()

        evidence = GraphEvidence(
            relationship_id=relationship.id,
            document_id=document_id,
            chunk_id="node-0007",
            page_number=3,
            source_text="Acme Corp shall provide services to Globex LLC.",
        )
        session.add(evidence)
        await session.commit()

        relationship_id = relationship.id

    # Reload from a fresh session and walk the full provenance chain:
    # relationship -> evidence -> document/chunk/page.
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(GraphRelationship).where(GraphRelationship.id == relationship_id)
        )
        loaded = result.scalar_one()
        assert loaded.relationship_type == "provides_services_to"
        assert loaded.confidence == pytest.approx(0.92)

        result = await session.execute(
            select(GraphEvidence).where(GraphEvidence.relationship_id == relationship_id)
        )
        loaded_evidence = result.scalar_one()
        assert loaded_evidence.document_id == document_id
        assert loaded_evidence.chunk_id == "node-0007"
        assert loaded_evidence.page_number == 3
        assert "Acme Corp shall provide services" in loaded_evidence.source_text


@pytest.mark.asyncio
async def test_duplicate_entity_on_reindex_is_rejected(
    client: AsyncClient, register_and_login
) -> None:
    """Re-indexing a document must not create duplicate entities.

    The ingestion service is expected to check-then-skip (or
    upsert) on this same key; this test asserts the DB-level
    constraint that makes that safe is actually in place.
    """
    headers = _auth_headers(await register_and_login(email="graph2@example.com"))
    document_id = await _create_document(client, headers, "Vendor Services Agreement B")

    async with AsyncSessionLocal() as session:
        session.add(
            GraphEntity(
                document_id=document_id,
                name="Acme Corp",
                canonical_name="acme corp",
                entity_type="organization",
            )
        )
        await session.commit()

    async with AsyncSessionLocal() as session:
        session.add(
            GraphEntity(
                document_id=document_id,
                name="ACME CORP",  # different surface form, same canonical_name
                canonical_name="acme corp",
                entity_type="organization",
            )
        )
        with pytest.raises(IntegrityError):
            await session.commit()


@pytest.mark.asyncio
async def test_duplicate_relationship_on_reindex_is_rejected(
    client: AsyncClient, register_and_login
) -> None:
    headers = _auth_headers(await register_and_login(email="graph3@example.com"))
    document_id = await _create_document(client, headers, "Vendor Services Agreement C")

    async with AsyncSessionLocal() as session:
        source = GraphEntity(
            document_id=document_id,
            name="Acme Corp",
            canonical_name="acme corp",
            entity_type="organization",
        )
        target = GraphEntity(
            document_id=document_id,
            name="Globex LLC",
            canonical_name="globex llc",
            entity_type="organization",
        )
        session.add_all([source, target])
        await session.flush()

        session.add(
            GraphRelationship(
                document_id=document_id,
                source_entity_id=source.id,
                target_entity_id=target.id,
                relationship_type="provides_services_to",
            )
        )
        await session.commit()

        source_id, target_id = source.id, target.id

    async with AsyncSessionLocal() as session:
        session.add(
            GraphRelationship(
                document_id=document_id,
                source_entity_id=source_id,
                target_entity_id=target_id,
                relationship_type="provides_services_to",
            )
        )
        with pytest.raises(IntegrityError):
            await session.commit()


@pytest.mark.asyncio
async def test_duplicate_evidence_for_same_chunk_is_rejected(
    client: AsyncClient, register_and_login
) -> None:
    headers = _auth_headers(await register_and_login(email="graph4@example.com"))
    document_id = await _create_document(client, headers, "Vendor Services Agreement D")

    async with AsyncSessionLocal() as session:
        source = GraphEntity(
            document_id=document_id,
            name="Acme Corp",
            canonical_name="acme corp",
            entity_type="organization",
        )
        target = GraphEntity(
            document_id=document_id,
            name="Globex LLC",
            canonical_name="globex llc",
            entity_type="organization",
        )
        session.add_all([source, target])
        await session.flush()

        relationship = GraphRelationship(
            document_id=document_id,
            source_entity_id=source.id,
            target_entity_id=target.id,
            relationship_type="provides_services_to",
        )
        session.add(relationship)
        await session.flush()

        session.add(
            GraphEvidence(
                relationship_id=relationship.id,
                document_id=document_id,
                chunk_id="node-0007",
                source_text="Acme Corp shall provide services to Globex LLC.",
            )
        )
        await session.commit()

        relationship_id = relationship.id

    async with AsyncSessionLocal() as session:
        session.add(
            GraphEvidence(
                relationship_id=relationship_id,
                document_id=document_id,
                chunk_id="node-0007",  # same chunk re-extracted on re-index
                source_text="Acme Corp shall provide services to Globex LLC.",
            )
        )
        with pytest.raises(IntegrityError):
            await session.commit()


@pytest.mark.asyncio
async def test_deleting_document_cascades_to_graph_tables(
    client: AsyncClient, register_and_login
) -> None:
    """Deleting a Document must cascade through entities, relationships,
    and evidence -- no orphaned graph rows left behind."""
    headers = _auth_headers(await register_and_login(email="graph5@example.com"))
    document_id = await _create_document(client, headers, "Vendor Services Agreement E")

    async with AsyncSessionLocal() as session:
        source = GraphEntity(
            document_id=document_id,
            name="Acme Corp",
            canonical_name="acme corp",
            entity_type="organization",
        )
        target = GraphEntity(
            document_id=document_id,
            name="Globex LLC",
            canonical_name="globex llc",
            entity_type="organization",
        )
        session.add_all([source, target])
        await session.flush()

        relationship = GraphRelationship(
            document_id=document_id,
            source_entity_id=source.id,
            target_entity_id=target.id,
            relationship_type="provides_services_to",
        )
        session.add(relationship)
        await session.flush()

        session.add(
            GraphEvidence(
                relationship_id=relationship.id,
                document_id=document_id,
                chunk_id="node-0007",
                source_text="Acme Corp shall provide services to Globex LLC.",
            )
        )
        await session.commit()

    async with AsyncSessionLocal() as session:
        document = await session.get(Document, document_id)
        await session.delete(document)
        await session.commit()

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

        assert entities == []
        assert relationships == []
        assert evidence_rows == []
