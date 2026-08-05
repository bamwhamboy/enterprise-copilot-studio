"""Conversation memory service.

Session and short-term memory: loads/appends conversation history,
isolated by (user_id, copilot_id). This is what the chat orchestrator
calls to load history before running the workflow, and to persist each
turn afterward.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.logging import get_logger
from app.llm.models import LLMMessage
from app.models.conversation import ConversationMessage, ConversationSession
from app.repositories.conversation_repository import (
    ConversationMessageRepository,
    ConversationSessionRepository,
)

logger = get_logger(__name__)


class ConversationMemoryService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self._settings = settings
        self.sessions = ConversationSessionRepository(session)
        self.messages = ConversationMessageRepository(session)

    async def get_or_create_session(
        self,
        *,
        user_id: str,
        copilot_id: uuid.UUID,
        session_id: uuid.UUID | None = None,
    ) -> ConversationSession:
        """Fetch an existing session by id, or start a new one.

        Isolation is enforced here: a caller can only resume a session
        that actually belongs to (user_id, copilot_id) — a mismatched
        session_id is treated as "start fresh" rather than leaking
        another user's/copilot's history.
        """
        if session_id is not None:
            existing = await self.sessions.get(session_id)
            if (
                existing is not None
                and existing.user_id == user_id
                and existing.copilot_id == copilot_id
            ):
                return existing
            logger.warning(
                "Session %s not found or doesn't belong to user=%s copilot=%s — starting new session",
                session_id,
                user_id,
                copilot_id,
            )

        new_session = ConversationSession(user_id=user_id, copilot_id=copilot_id)
        new_session = await self.sessions.create(new_session)
        await self.session.commit()
        logger.info(
            "Created conversation session %s for user=%s copilot=%s",
            new_session.id,
            user_id,
            copilot_id,
        )
        return new_session

    async def load_history(self, session_id: uuid.UUID) -> list[LLMMessage]:
        """Load recent conversation history as LLM-ready messages.

        Windowed to ``Settings.MAX_CONVERSATION_HISTORY_MESSAGES`` — this
        is the short-term memory boundary; long-term memory (retrieval
        over older history) can be layered on top later without
        changing this method's contract.
        """
        messages = await self.messages.list_for_session(
            session_id, limit=self._settings.MAX_CONVERSATION_HISTORY_MESSAGES
        )
        return [
            LLMMessage(role=m.role, content=m.content) for m in messages if m.role != "system"
        ]

    async def append_message(
        self, session_id: uuid.UUID, *, role: str, content: str
    ) -> ConversationMessage:
        message = ConversationMessage(session_id=session_id, role=role, content=content)
        message = await self.messages.create(message)
        await self.session.commit()
        return message
