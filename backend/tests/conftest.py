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
from llama_index.core.embeddings import MockEmbedding
from qdrant_client import QdrantClient

from app.core.dependencies import get_embed_model, get_qdrant_client
from app.database.base import Base
from app.database.session import AsyncSessionLocal, engine
from app.main import app
from app.models import Copilot, Document, KnowledgeSource  # noqa: F401  (populates Base.metadata)

# Sprint 3B: override the real HuggingFaceEmbedding (needs network access to
# huggingface.co, unavailable in this environment) with LlamaIndex's own
# MockEmbedding — same interface, deterministic, no network. Qdrant runs
# in-memory rather than against a real server. These overrides test the
# indexing/retrieval *pipeline* for real; they don't validate embedding
# quality, which isn't this sprint's concern.
_test_qdrant_client = QdrantClient(":memory:")
app.dependency_overrides[get_embed_model] = lambda: MockEmbedding(embed_dim=384)
app.dependency_overrides[get_qdrant_client] = lambda: _test_qdrant_client


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    """Create all tables once for the test session, drop them afterward."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Seed the five RBAC roles. In a real deployment these come from the
    # Sprint 6 Alembic migration's data-seeding step (see
    # alembic/versions/..._add_auth_rbac_and_multi_tenancy_tables.py) --
    # but the test suite builds its schema via Base.metadata.create_all()
    # (fast, no migration history needed), which only creates tables, not
    # migration-embedded seed data. Seed it here instead, once per session.
    from app.models.role import ALL_ROLES, Role

    async with AsyncSessionLocal() as session:
        session.add_all([Role(name=name) for name in ALL_ROLES])
        await session.commit()

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


@pytest_asyncio.fixture
def register_and_login(client: AsyncClient):
    """Factory fixture: register (or reuse) a user and return their TokenResponse dict.

    Usage: ``tokens = await register_and_login(email="a@b.com")`` then
    ``headers = {"Authorization": f"Bearer {tokens['access_token']}"}``.
    Shared here (rather than duplicated per test file) since most test
    modules now need an authenticated user to exercise protected chat
    endpoints.
    """

    async def _factory(
        *,
        email: str,
        organization_name: str = "Test Org",
        password: str = "TestPass123",
    ) -> dict:
        await client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password, "organization_name": organization_name},
        )
        response = await client.post(
            "/api/v1/auth/login", data={"username": email, "password": password}
        )
        return response.json()

    return _factory


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine_after_test():
    """Drop pooled connections after each test.

    pytest-asyncio gives each test function its own event loop by
    default; without this, a connection opened in one test's loop gets
    reused (and fails) in the next test's loop.
    """
    yield
    await engine.dispose()
