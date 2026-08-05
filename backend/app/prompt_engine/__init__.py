"""Prompt engine: reusable prompt template definitions and rendering.

New in Sprint 4. ``templates.py`` defines ``PromptTemplate`` (system /
developer / user roles, with named variables) and ``renderer.py``
renders a template — or a full multi-role sequence of them — into
``LLMMessage`` objects the (future) LLM Gateway can consume.

Pure string templating — no AI logic, no network calls.
"""
