"""Repository layer: encapsulates all direct database access.

Services depend on repositories, never on SQLAlchemy sessions or query
construction directly — this keeps persistence concerns out of the
business-logic layer and makes repositories the single place that knows
how each entity is actually stored/queried.
"""
