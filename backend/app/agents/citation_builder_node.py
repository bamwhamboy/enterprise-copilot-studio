"""Citation builder node.

Extracts citations from the retrieved chunks used to ground the response.
Human-review responses intentionally contain no citations because they are
not verified answers.
"""

from __future__ import annotations

from app.agents.state import ChatState


async def citation_builder_node(state: ChatState) -> dict:
    if state.get("human_review_required", False):
        return {"citations": []}

    chunks = state.get("retrieved_chunks", [])
    citations = [chunk.citation for chunk in chunks]
    return {"citations": citations}
