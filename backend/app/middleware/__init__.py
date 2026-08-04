"""HTTP middleware: cross-cutting request/response concerns.

Currently contains only request-context logging (request IDs, timing).
Auth, rate limiting, and AI-specific middleware (prompt sanitization,
guardrails) will be added in later phases.
"""
