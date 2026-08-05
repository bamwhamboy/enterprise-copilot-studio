"""Tests for conversation memory (Sprint 5)."""

import uuid

import pytest

from app.core.config import get_settings
from app.memory.conversation_memory_service import ConversationMemoryService


@pytest.mark.asyncio
async def test_get_or_create_session_creates_new_session(client) -> None:
    from app.database.session import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        service = ConversationMemoryService(session, get_settings())
        copilot_id = uuid.uuid4()

        created = await service.get_or_create_session(user_id="alice", copilot_id=copilot_id)
        assert created.user_id == "alice"
        assert created.copilot_id == copilot_id


@pytest.mark.asyncio
async def test_session_isolation_by_user_and_copilot(client) -> None:
    from app.database.session import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        service = ConversationMemoryService(session, get_settings())
        copilot_id = uuid.uuid4()

        session1 = await service.get_or_create_session(user_id="alice", copilot_id=copilot_id)

        # Different user, same copilot, same session_id -> isolation kicks
        # in and a NEW session is created rather than reusing alice's.
        session2 = await service.get_or_create_session(
            user_id="bob", copilot_id=copilot_id, session_id=session1.id
        )

        assert session2.id != session1.id
        assert session2.user_id == "bob"


@pytest.mark.asyncio
async def test_append_and_load_history(client) -> None:
    from app.database.session import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        service = ConversationMemoryService(session, get_settings())
        chat_session = await service.get_or_create_session(
            user_id="carol", copilot_id=uuid.uuid4()
        )

        await service.append_message(chat_session.id, role="user", content="Hello")
        await service.append_message(chat_session.id, role="assistant", content="Hi there!")

        history = await service.load_history(chat_session.id)

        assert len(history) == 2
        assert history[0].role == "user"
        assert history[0].content == "Hello"
        assert history[1].role == "assistant"


@pytest.mark.asyncio
async def test_history_is_windowed_to_max_messages(client, monkeypatch) -> None:
    from app.database.session import AsyncSessionLocal

    settings = get_settings()
    monkeypatch.setattr(settings, "MAX_CONVERSATION_HISTORY_MESSAGES", 2)

    async with AsyncSessionLocal() as session:
        service = ConversationMemoryService(session, settings)
        chat_session = await service.get_or_create_session(
            user_id="dave", copilot_id=uuid.uuid4()
        )

        for i in range(5):
            await service.append_message(chat_session.id, role="user", content=f"message {i}")

        history = await service.load_history(chat_session.id)

        assert len(history) == 2
        # Windowing keeps the most recent messages, still chronological.
        assert history[-1].content == "message 4"
