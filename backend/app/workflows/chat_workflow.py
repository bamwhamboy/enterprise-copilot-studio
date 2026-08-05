"""Chat workflow.

Wires the five specialized nodes (planner, retrieval, context builder,
response generator, citation builder) into a single LangGraph
StateGraph. Deliberately linear for this sprint — the graph structure
is what makes adding branches later (a tool-use node, a re-planning
loop, parallel retrieval strategies) a matter of adding nodes/edges,
not refactoring this function or any caller.
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.agents.citation_builder_node import citation_builder_node
from app.agents.context_builder_node import make_context_builder_node
from app.agents.planner_node import planner_node
from app.agents.response_generator_node import make_response_generator_node
from app.agents.retrieval_node import make_retrieval_node
from app.agents.state import ChatState
from app.core.config import Settings
from app.guardrails.guardrails_runtime import GuardrailsRuntime
from app.knowledge_engine.compression.compression_service import ContextCompressionService
from app.knowledge_engine.retrieval.hybrid_retriever import HybridRetriever
from app.llm.gateway import LLMGateway
from app.prompt_engine.renderer import PromptRenderer


def build_chat_workflow(
    settings: Settings,
    retriever: HybridRetriever,
    compression: ContextCompressionService,
    renderer: PromptRenderer,
    gateway: LLMGateway,
    guardrails: GuardrailsRuntime,
):
    """Compile the chat LangGraph workflow, wired with all runtime dependencies."""
    graph = StateGraph(ChatState)

    graph.add_node("planner", planner_node)
    graph.add_node("retrieval", make_retrieval_node(settings, retriever, compression))
    graph.add_node("context_builder", make_context_builder_node(renderer))
    graph.add_node(
        "response_generator", make_response_generator_node(settings, gateway, guardrails)
    )
    graph.add_node("citation_builder", citation_builder_node)

    graph.set_entry_point("planner")
    graph.add_edge("planner", "retrieval")
    graph.add_edge("retrieval", "context_builder")
    graph.add_edge("context_builder", "response_generator")
    graph.add_edge("response_generator", "citation_builder")
    graph.add_edge("citation_builder", END)

    return graph.compile()
