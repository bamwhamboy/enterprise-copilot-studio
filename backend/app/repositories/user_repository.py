"""Repository for the User entity."""

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    async def get(self, id) -> User | None:
        stmt = (
            select(User)
            .where(User.id == id)
            .options(selectinload(User.organization), selectinload(User.role))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        stmt = (
            select(User)
            .where(User.email == email)
            .options(selectinload(User.organization), selectinload(User.role))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
