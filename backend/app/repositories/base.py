"""Generic base repository.

Provides the CRUD operations shared by every entity in this sprint.
Concrete repositories set ``model`` and add relationship-aware query
methods (e.g. eager-loading) on top of this where needed.

All current models expose ``created_at``, so ``list_all()`` orders by it
by default; a subclass can override ``list_all()`` if that ever stops
holding.
"""

import uuid
from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    model: type[ModelType]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, id: uuid.UUID) -> ModelType | None:
        return await self.session.get(self.model, id)

    async def list_all(self, *, offset: int = 0, limit: int = 100) -> list[ModelType]:
        stmt = (
            select(self.model)
            .order_by(self.model.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, instance: ModelType) -> ModelType:
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def delete(self, instance: ModelType) -> None:
        await self.session.delete(instance)
        await self.session.flush()
