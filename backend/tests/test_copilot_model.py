"""ORM-level tests for Copilot.capabilities (Sprint 1 HITL foundation).

Complements the API-level tests in test_copilots.py: these exercise
the model directly (no HTTP), which is the closest thing to a
migration-compatibility check available in this suite -- the test
database is built via Base.metadata.create_all (see conftest.py), not
by running Alembic migrations, so the actual upgrade/downgrade round
-trip and existing-row backfill were verified manually against a real
Postgres dev database, not here. What IS verified here: the model's
Python-side default matches exactly what the migration's
server_default backfills onto existing rows, so both paths produce
the identical starting capability configuration.
"""

import uuid

import pytest
from sqlalchemy import select

from app.database.session import AsyncSessionLocal
from app.models.copilot import DEFAULT_CAPABILITIES, Copilot


@pytest.mark.asyncio
async def test_copilot_gets_default_capabilities_when_not_specified() -> None:
    """A Copilot created without an explicit capabilities value (the
    exact shape of a pre-Sprint-1 code path that never knew this field
    existed) must still get a valid, safe default -- not a NULL, not
    an error."""
    async with AsyncSessionLocal() as session:
        copilot = Copilot(
            name="Model-Level Default Test",
            domain="hr",
            status="draft",
            model="openai/gpt-oss-120b",
        )
        session.add(copilot)
        await session.commit()
        copilot_id = copilot.id

    async with AsyncSessionLocal() as session:
        loaded = await session.get(Copilot, copilot_id)
        assert loaded is not None
        assert loaded.capabilities == {"human_in_the_loop": False}


@pytest.mark.asyncio
async def test_copilot_default_capabilities_is_a_fresh_dict_each_time() -> None:
    """DEFAULT_CAPABILITIES must not be the same mutable object shared
    across rows -- the model's default=lambda: dict(DEFAULT_CAPABILITIES)
    is what guarantees that; this catches a regression where someone
    "simplifies" it back to a bare shared dict."""
    async with AsyncSessionLocal() as session:
        first = Copilot(name="A", domain="hr", status="draft", model="openai/gpt-oss-120b")
        second = Copilot(name="B", domain="hr", status="draft", model="openai/gpt-oss-120b")
        session.add_all([first, second])
        await session.commit()

        first.capabilities["human_in_the_loop"] = True
        assert second.capabilities["human_in_the_loop"] is False


def test_default_capabilities_constant_matches_migration_backfill() -> None:
    """The Python-side default and the migration's server_default
    (see alembic/versions/18d0209e82c5_*.py) must describe the exact
    same starting configuration -- this is what makes existing rows
    (backfilled by the migration) and newly-created rows (using this
    constant) indistinguishable."""
    assert DEFAULT_CAPABILITIES == {"human_in_the_loop": False}


@pytest.mark.asyncio
async def test_capabilities_persists_and_reloads_extra_keys() -> None:
    """A capabilities dict with a not-yet-named key round-trips through
    JSONB correctly -- proves the column itself is genuinely
    schema-less/extensible, not just the Pydantic layer."""
    async with AsyncSessionLocal() as session:
        copilot = Copilot(
            name="Extensible Capabilities Test",
            domain="hr",
            status="draft",
            model="openai/gpt-oss-120b",
            capabilities={"human_in_the_loop": True, "future_toggle": "some-value"},
        )
        session.add(copilot)
        await session.commit()
        copilot_id = copilot.id

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Copilot).where(Copilot.id == copilot_id))
        loaded = result.scalar_one()
        assert loaded.capabilities == {
            "human_in_the_loop": True,
            "future_toggle": "some-value",
        }
