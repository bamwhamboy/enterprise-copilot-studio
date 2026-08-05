"""Citation builder node.

Extracts citations from the retrieved chunks used to ground the
response: document name, knowledge source, page number, section, chunk
number (Citation, defined in Sprint 3B's knowledge_engine.models).
"""

from __future__ import annotations

from app.agents.state import ChatState


async def citation_builder_node(state: ChatState) -> dict:
    chunks = state.get("retrieved_chunks", [])
    citations = [chunk.citation for chunk in chunks]
    return {"citations": citations}
