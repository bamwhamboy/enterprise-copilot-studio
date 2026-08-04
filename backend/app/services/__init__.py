"""Business logic / service layer.

Routers stay thin and delegate to services here. Services depend on
repositories (never on raw SQLAlchemy sessions or query construction)
and raise domain exceptions from ``app.core.exceptions`` rather than
HTTP exceptions directly.
"""
