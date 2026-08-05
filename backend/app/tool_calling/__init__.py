"""Tool calling.

Sprint 5 implements the generic tool framework: ``base.py`` (the
``Tool`` interface + ``ToolResult``), ``registry.py`` (``ToolRegistry``,
where tools are registered by name and discovered at call time), and
one production tool under ``tools/`` — ``KnowledgeSearchTool``, wrapping
the existing Hybrid Hierarchical RAG retrieval.

Adding a new tool (SQL, REST API, calculator, web search, ...) means
implementing the ``Tool`` interface and registering it — no changes to
the registry, the LangGraph tool-use node, or the chat orchestrator.
"""
