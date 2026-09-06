"""Shared pytest fixtures."""

import os
import shutil
import tempfile

# Must be set before any `app.*` module is imported.
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/ecs_test"
)
_TEST_STORAGE_DIR = tempfile.mkdtemp(prefix="ecs-test-storage-")
os.environ.setdefault("STORAGE_DIR", _TEST_STORAGE_DIR)
# Online Weave/Groq evaluation is an external production dependency. The
# normal unit suite remains deterministic and offline; evaluator behavior is
# covered separately with mocked scorer/gateway components.
os.environ.setdefault("RESPONSE_EVALUATION_ENABLED", "false")

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from llama_index.core.embeddings import MockEmbedding
from qdrant_client import QdrantClient

from app.core.dependencies import get_embed_model, get_qdrant_client
from app.database.base import Base
from app.database.session import AsyncSessionLocal, engine
from app.main import app
from app.models import Copilot, Document, KnowledgeSource  # noqa: F401

_test_qdrant_client = QdrantClient(":memory:")
app.dependency_overrides[get_embed_model] = lambda: MockEmbedding(embed_dim=384)
app.dependency_overrides[get_qdrant_client] = lambda: _test_qdrant_client


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    """Create all tables once for the test session, drop them afterward."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    from app.models.role import ALL_ROLES, Role

    async with AsyncSessionLocal() as session:
        session.add_all([Role(name=name) for name in ALL_ROLES])
        await session.commit()

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
    """Factory fixture for registering and authenticating a test user."""

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
    """Drop pooled connections after each test."""
    yield
    await engine.dispose()
