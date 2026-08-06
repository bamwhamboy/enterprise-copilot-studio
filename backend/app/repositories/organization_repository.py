"""Repositories for Organization and Role.

Combined into one file: both are simple, low-logic lookup tables (no
entity-specific query methods beyond what BaseRepository already gives
plus a by-name lookup), so a dedicated file each would be pure
boilerplate.
"""

from sqlalchemy import select

from app.models.organization import Organization
from app.models.role import Role
from app.repositories.base import BaseRepository


class OrganizationRepository(BaseRepository[Organization]):
    model = Organization

    async def get_by_name(self, name: str) -> Organization | None:
        stmt = select(Organization).where(Organization.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class RoleRepository(BaseRepository[Role]):
    model = Role

    async def get_by_name(self, name: str) -> Role | None:
        stmt = select(Role).where(Role.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self, *, offset: int = 0, limit: int = 100) -> list[Role]:
        # Override: BaseRepository.list_all() orders by created_at, which
        # Role doesn't have (a small, timestamp-free reference table).
        stmt = select(Role).order_by(Role.name).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
