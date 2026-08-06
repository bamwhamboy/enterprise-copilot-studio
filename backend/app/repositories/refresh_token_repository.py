"""Repository for RefreshToken.

Tokens are looked up by their SHA-256 hash (never the raw value --
hashing happens in AuthService, this repository only ever sees hashes).
"""

from datetime import datetime, timezone

from sqlalchemy import select

from app.models.refresh_token import RefreshToken
from app.repositories.base import BaseRepository


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    model = RefreshToken

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    def is_valid(self, token: RefreshToken) -> bool:
        return not token.revoked and token.expires_at > datetime.now(timezone.utc)

    async def revoke(self, token: RefreshToken) -> None:
        token.revoked = True
        await self.session.flush()

    async def revoke_all_for_user(self, user_id) -> None:
        """Used on logout-everywhere / password-change style flows."""
        stmt = select(RefreshToken).where(
            RefreshToken.user_id == user_id, RefreshToken.revoked.is_(False)
        )
        result = await self.session.execute(stmt)
        for token in result.scalars().all():
            token.revoked = True
        await self.session.flush()
