"""Repository for ConversationSession / ConversationMessage."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.conversation import ConversationMessage, ConversationSession
from app.repositories.base import BaseRepository


class ConversationSessionRepository(BaseRepository[ConversationSession]):
    model = ConversationSession

    async def get(self, id: uuid.UUID) -> ConversationSession | None:
        stmt = (
            select(ConversationSession)
            .where(ConversationSession.id == id)
            .options(selectinload(ConversationSession.messages))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_user_and_copilot(
        self, *, user_id: str, copilot_id: uuid.UUID
    ) -> list[ConversationSession]:
        stmt = (
            select(ConversationSession)
            .where(
                ConversationSession.user_id == user_id,
                ConversationSession.copilot_id == copilot_id,
            )
            .order_by(ConversationSession.updated_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class ConversationMessageRepository(BaseRepository[ConversationMessage]):
    model = ConversationMessage

    async def list_for_session(
        self, session_id: uuid.UUID, *, limit: int | None = None
    ) -> list[ConversationMessage]:
        stmt = (
            select(ConversationMessage)
            .where(ConversationMessage.session_id == session_id)
            .order_by(ConversationMessage.created_at.asc())
        )
        result = await self.session.execute(stmt)
        messages = list(result.scalars().all())
        if limit is not None and len(messages) > limit:
            # Keep the most recent `limit` messages, still chronological.
            messages = messages[-limit:]
        return messages
