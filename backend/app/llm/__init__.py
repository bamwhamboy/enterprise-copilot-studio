"""LLM gateway and provider abstraction.

Sprint 4 implements the **routing/configuration layer**: ``gateway.py``
(provider selection + the ``generate``/``stream``/``health`` interface),
``providers.py`` (per-provider config + client interface for OpenAI,
Groq, Azure OpenAI, and Anthropic), and ``models.py`` (shared request/
response contracts).

No network calls are made anywhere in this package — provider clients'
``generate``/``stream`` deliberately raise ``NotImplementedError``.
LiteLLM integration and real API calls are a later sprint.
"""
