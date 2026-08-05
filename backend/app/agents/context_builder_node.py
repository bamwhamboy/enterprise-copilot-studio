"""Context builder node.

Assembles the final message list sent to the LLM: system prompt +
retrieved context + conversation history + the user's message. Uses
the existing Prompt Engine (Sprint 4) for templated rendering.
"""

from __future__ import annotations

from app.agents.state import ChatState
from app.llm.models import LLMMessage
from app.prompt_engine.renderer import PromptRenderer
from app.prompt_engine.templates import PromptTemplate

SYSTEM_TEMPLATE = PromptTemplate(
    name="chat_system",
    role="system",
    template="You are {copilot_name}, an enterprise AI assistant for the {domain} domain.",
    variables=["copilot_name", "domain"],
    description="Baseline chat system prompt.",
)

CONTEXT_TEMPLATE = PromptTemplate(
    name="rag_context",
    role="system",
    template=(
        "Use the following retrieved context to answer the user's question. "
        "If the context doesn't contain the answer, say you don't know — do "
        "not make anything up.\n\n{context}"
    ),
    variables=["context"],
    description="Injects retrieved RAG context ahead of the user's question.",
)


def make_context_builder_node(renderer: PromptRenderer):
    async def context_builder_node(state: ChatState) -> dict:
        chunks = state.get("retrieved_chunks", [])
        context_text = (
            "\n\n".join(
                f"[{i + 1}] ({c.citation.document_name}) {c.text}" for i, c in enumerate(chunks)
            )
            or "No relevant context was found."
        )

        system_message = renderer.render(
            SYSTEM_TEMPLATE,
            {
                "copilot_name": state.get("copilot_name", "Copilot"),
                "domain": state.get("domain", "general"),
            },
        )
        context_message = renderer.render(CONTEXT_TEMPLATE, {"context": context_text})

        messages = [
            LLMMessage(role="system", content=system_message),
            LLMMessage(role="system", content=context_message),
            *state.get("history", []),
            LLMMessage(role="user", content=state["user_message"]),
        ]
        return {"llm_messages": messages}

    return context_builder_node
