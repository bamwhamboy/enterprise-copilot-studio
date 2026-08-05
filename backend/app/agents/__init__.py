"""LangGraph workflow nodes ("agents").

Five specialized nodes compose the chat workflow (see
app/workflows/chat_workflow.py): planner, retrieval, context_builder,
response_generator, citation_builder. Each is a plain async function
operating on the shared ChatState (state.py) -- dependency-injected via
a `make_*_node(deps...)` factory closure where a node needs services
(retriever, LLM gateway, etc.), or a bare function where it doesn't.

Adding a new node (e.g. a tool-use node, a re-planning loop) means
adding one more file here plus one more graph.add_node()/add_edge() in
the workflow -- no changes to existing nodes required.
"""
