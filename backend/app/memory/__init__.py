"""Conversation and context memory.

Sprint 5 implements session/short-term memory:
``conversation_memory_service.py`` (``ConversationMemoryService``), backed
by the ``ConversationSession``/``ConversationMessage`` models in
``app/models/conversation.py``. Isolated by (user_id, copilot_id).

Designed so long-term memory (e.g. summarized/vector-indexed history
beyond the recent-message window) can be added later as an additional
method on this same service, without changing its public interface or
any caller.
"""
