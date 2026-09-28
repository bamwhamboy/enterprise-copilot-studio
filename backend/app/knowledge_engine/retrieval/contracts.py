"""Shared retrieval contracts for Enterprise Copilot V2."""

from enum import Enum


class RetrievalMode(str, Enum):
    HYBRID = "hybrid"
    GRAPH = "graph"
    HYBRID_GRAPH = "hybrid_graph"
