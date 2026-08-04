"""Shared pytest fixtures."""

import os
import shutil
import tempfile

# Must be set before any `app.*` module is imported, since Settings is
# read (and cached) at first import — this routes the test suite at a
# dedicated database and an isolated storage directory so it never
# touches development data or files.
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/ecs_test"
)
_TEST_STORAGE_DIR = tempfile.mkdtemp(prefix="ecs-test-storage-")
os.environ.setdefault("STORAGE_DIR", _TEST_STORAGE_DIR)

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.database.base import Base
from app.database.session import engine
from app.main import app
from app.models import Copilot, Document, KnowledgeSource  # noqa: F401  (populates Base.metadata)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    """Create all tables once for the test session, drop them afterward."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Drop pooled connections opened during setup — they belong to this
    # fixture's event loop, which differs from the first test's loop.
    await engine.dispose()

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    shutil.rmtree(_TEST_STORAGE_DIR, ignore_errors=True)


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    """Async HTTP client bound directly to the ASGI app (no network/server)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine_after_test():
    """Drop pooled connections after each test.

    pytest-asyncio gives each test function its own event loop by
    default; without this, a connection opened in one test's loop gets
    reused (and fails) in the next test's loop.
    """
    yield
    await engine.dispose()
