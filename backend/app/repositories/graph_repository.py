"""Repositories for GraphEntity / GraphRelationship / GraphEvidence.

Each ``find_by_*`` method here queries by the same natural key its
model's unique constraint covers (see ``app/models/graph.py``) -- these
are the lookups ``GraphExtractionService`` uses to make re-running
extraction for a document idempotent (check-then-create instead of
create-and-catch, with the DB constraint as the backstop for races).
"""

import uuid

from sqlalchemy import select

from app.models.graph import GraphEntity, GraphEvidence, GraphRelationship
from app.repositories.base import BaseRepository


class GraphEntityRepository(BaseRepository[GraphEntity]):
    model = GraphEntity

    async def find_by_canonical_name(
        self, *, document_id: uuid.UUID, canonical_name: str, entity_type: str
    ) -> GraphEntity | None:
        stmt = select(GraphEntity).where(
            GraphEntity.document_id == document_id,
            GraphEntity.canonical_name == canonical_name,
            GraphEntity.entity_type == entity_type,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_document(self, document_id: uuid.UUID) -> list[GraphEntity]:
        stmt = select(GraphEntity).where(GraphEntity.document_id == document_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class GraphRelationshipRepository(BaseRepository[GraphRelationship]):
    model = GraphRelationship

    async def find_by_natural_key(
        self,
        *,
        document_id: uuid.UUID,
        source_entity_id: uuid.UUID,
        target_entity_id: uuid.UUID,
        relationship_type: str,
    ) -> GraphRelationship | None:
        stmt = select(GraphRelationship).where(
            GraphRelationship.document_id == document_id,
            GraphRelationship.source_entity_id == source_entity_id,
            GraphRelationship.target_entity_id == target_entity_id,
            GraphRelationship.relationship_type == relationship_type,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_document(self, document_id: uuid.UUID) -> list[GraphRelationship]:
        stmt = select(GraphRelationship).where(GraphRelationship.document_id == document_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class GraphEvidenceRepository(BaseRepository[GraphEvidence]):
    model = GraphEvidence

    async def find_by_relationship_and_chunk(
        self, *, relationship_id: uuid.UUID, chunk_id: str
    ) -> GraphEvidence | None:
        stmt = select(GraphEvidence).where(
            GraphEvidence.relationship_id == relationship_id,
            GraphEvidence.chunk_id == chunk_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_document(self, document_id: uuid.UUID) -> list[GraphEvidence]:
        stmt = select(GraphEvidence).where(GraphEvidence.document_id == document_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
