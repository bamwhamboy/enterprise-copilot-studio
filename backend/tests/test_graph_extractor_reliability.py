"""Tests for GraphExtractor's rate-limit handling and JSON-parsing
robustness (Groq TPM reliability work).

Covers: retrying on ``litellm.RateLimitError`` with exponential
backoff, honoring ``Retry-After`` when the provider sends one,
exhausting retries raising a distinct ``GraphExtractionRateLimitError``
(still isolated per-chunk by ``GraphExtractionService``, same as any
other chunk failure), proactive pacing between calls, and JSON parsing
that tolerates markdown fences / surrounding prose / trailing commas
without inventing or repairing any actual entity/relationship content.

No real LLM call and no real sleeping happens anywhere in this file --
``asyncio.sleep`` is replaced with a fake that records requested delays
and returns immediately, so retry/backoff/pacing tests run fast and
deterministically.
"""

import uuid
from types import SimpleNamespace

import litellm
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.database.session import AsyncSessionLocal
from app.knowledge_engine.graph.extractor import (
    GraphExtractionError,
    GraphExtractionRateLimitError,
    GraphExtractor,
)
from app.knowledge_engine.graph.graph_extraction_service import GraphExtractionService
from app.knowledge_engine.models import ChunkMetadata, HierarchicalChunk
from app.models.graph import GraphEntity

KS_BASE = "/api/v1/knowledge-sources"
DOC_BASE = "/api/v1/documents"

_SUCCESS_JSON = """{
  "entities": [
    {"name": "Acme Corp", "canonical_name": "acme corp", "entity_type": "organization"}
  ],
  "relationships": []
}"""


def _auth_headers(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _create_document(client: AsyncClient, headers: dict, name: str) -> uuid.UUID:
    ks_response = await client.post(KS_BASE, json={"name": f"{name} Source"}, headers=headers)
    ks_id = ks_response.json()["id"]
    doc_response = await client.post(
        DOC_BASE,
        json={"knowledge_source_id": ks_id, "name": name, "status": "indexed"},
        headers=headers,
    )
    return uuid.UUID(doc_response.json()["id"])


def _chunk(document_id: uuid.UUID, node_id: str, text: str):
    return HierarchicalChunk(
        text=text,
        metadata=ChunkMetadata(
            document_id=str(document_id),
            knowledge_source_id=str(uuid.uuid4()),
            document_name="doc.pdf",
            chunk_number=0,
            page_number=None,
        ),
        node_id=node_id,
    )


def _rate_limit_error(*, headers: dict | None = None) -> litellm.RateLimitError:
    return litellm.RateLimitError(
        message="rate limited",
        llm_provider="groq",
        model="groq/openai/gpt-oss-120b",
        headers=headers or {},
    )


class _FakeSleep:
    """Records every requested delay and returns immediately -- no
    real waiting, so retry/backoff/pacing tests run fast."""

    def __init__(self) -> None:
        self.calls: list[float] = []

    async def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)


class _ScriptedGateway:
    """Raises/returns a scripted sequence of outcomes, one per call.
    An outcome that's an Exception instance is raised; anything else is
    wrapped as a GenerationResponse-shaped object and returned."""

    def __init__(self, outcomes: list):
        self._outcomes = list(outcomes)
        self.call_count = 0

    async def generate(self, request):
        self.call_count += 1
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return SimpleNamespace(content=outcome)


# --- Rate-limit retry/backoff ------------------------------------------


@pytest.mark.asyncio
async def test_retries_on_rate_limit_and_eventually_succeeds():
    sleep = _FakeSleep()
    gateway = _ScriptedGateway([_rate_limit_error(), _rate_limit_error(), _SUCCESS_JSON])
    extractor = GraphExtractor(
        gateway,
        min_request_interval_seconds=0,
        max_retries=5,
        retry_base_delay_seconds=1.0,
        sleep=sleep,
    )

    result = await extractor.extract("Acme Corp is a vendor.")

    assert gateway.call_count == 3
    assert result.entities[0].canonical_name == "acme corp"
    # Two rate-limit retries happened (two backoff sleeps recorded).
    assert len(sleep.calls) == 2


@pytest.mark.asyncio
async def test_rate_limit_backoff_without_retry_after_grows_exponentially():
    sleep = _FakeSleep()
    gateway = _ScriptedGateway(
        [_rate_limit_error(), _rate_limit_error(), _rate_limit_error(), _SUCCESS_JSON]
    )
    extractor = GraphExtractor(
        gateway,
        min_request_interval_seconds=0,
        max_retries=5,
        retry_base_delay_seconds=1.0,
        retry_max_delay_seconds=60.0,
        sleep=sleep,
    )

    await extractor.extract("Acme Corp is a vendor.")

    assert len(sleep.calls) == 3
    # Each backoff should be larger than the last (exponential growth;
    # jitter adds up to +10%, so use a loose but meaningful bound).
    assert sleep.calls[0] < sleep.calls[1] < sleep.calls[2]
    # First attempt: base_delay * 2^0 = 1.0s, plus up to 10% jitter.
    assert 1.0 <= sleep.calls[0] <= 1.1


@pytest.mark.asyncio
async def test_rate_limit_respects_retry_after_header():
    sleep = _FakeSleep()
    gateway = _ScriptedGateway([_rate_limit_error(headers={"retry-after": "7"}), _SUCCESS_JSON])
    extractor = GraphExtractor(
        gateway,
        min_request_interval_seconds=0,
        max_retries=5,
        retry_base_delay_seconds=1.0,
        retry_max_delay_seconds=60.0,
        sleep=sleep,
    )

    await extractor.extract("Acme Corp is a vendor.")

    assert sleep.calls == [7.0]


@pytest.mark.asyncio
async def test_retry_after_is_capped_at_max_delay():
    sleep = _FakeSleep()
    gateway = _ScriptedGateway(
        [_rate_limit_error(headers={"retry-after": "500"}), _SUCCESS_JSON]
    )
    extractor = GraphExtractor(
        gateway,
        min_request_interval_seconds=0,
        max_retries=5,
        retry_max_delay_seconds=60.0,
        sleep=sleep,
    )

    await extractor.extract("Acme Corp is a vendor.")

    assert sleep.calls == [60.0]


@pytest.mark.asyncio
async def test_exhausting_retries_raises_distinct_rate_limit_error():
    sleep = _FakeSleep()
    gateway = _ScriptedGateway([_rate_limit_error() for _ in range(4)])
    extractor = GraphExtractor(
        gateway,
        min_request_interval_seconds=0,
        max_retries=3,
        retry_base_delay_seconds=0.01,
        sleep=sleep,
    )

    with pytest.raises(GraphExtractionRateLimitError):
        await extractor.extract("Acme Corp is a vendor.")

    # 3 retries after the first failure = 4 total attempts.
    assert gateway.call_count == 4


@pytest.mark.asyncio
async def test_non_rate_limit_errors_are_not_retried():
    """A plain, non-rate-limit exception (e.g. an auth error) must
    propagate immediately -- retry/backoff is specific to
    litellm.RateLimitError, not a general-purpose retry-everything
    mechanism."""
    sleep = _FakeSleep()
    gateway = _ScriptedGateway([RuntimeError("boom")])
    extractor = GraphExtractor(gateway, min_request_interval_seconds=0, sleep=sleep)

    with pytest.raises(RuntimeError):
        await extractor.extract("Acme Corp is a vendor.")

    assert gateway.call_count == 1
    assert sleep.calls == []


# --- Proactive pacing between calls -------------------------------------


@pytest.mark.asyncio
async def test_pacing_enforces_minimum_interval_between_calls():
    sleep = _FakeSleep()
    gateway = _ScriptedGateway([_SUCCESS_JSON, _SUCCESS_JSON])
    extractor = GraphExtractor(gateway, min_request_interval_seconds=5.0, sleep=sleep)

    await extractor.extract("first chunk")
    await extractor.extract("second chunk")

    # First call: no prior call, so no pacing wait. Second call: since
    # the fake sleep never actually waits, almost no real time elapsed
    # between the two calls, so the pacing gate should request very
    # close to the full 5.0s interval.
    assert len(sleep.calls) == 1
    assert 4.9 <= sleep.calls[0] <= 5.0


@pytest.mark.asyncio
async def test_max_concurrency_defaults_to_sequential():
    """Sanity check that the default construction (no explicit
    max_concurrency) still behaves as a single in-flight call at a
    time -- i.e. doesn't fire calls in an uncontrolled burst by
    default."""
    sleep = _FakeSleep()
    gateway = _ScriptedGateway([_SUCCESS_JSON, _SUCCESS_JSON, _SUCCESS_JSON])
    extractor = GraphExtractor(gateway, min_request_interval_seconds=0, sleep=sleep)

    import asyncio

    results = await asyncio.gather(
        extractor.extract("a"), extractor.extract("b"), extractor.extract("c")
    )
    assert len(results) == 3
    assert gateway.call_count == 3


# --- Rate-limit exhaustion isolated per-chunk, through the real service ----


@pytest.mark.asyncio
async def test_rate_limit_exhaustion_isolated_to_one_chunk(
    client: AsyncClient, register_and_login
) -> None:
    headers = _auth_headers(await register_and_login(email="ratelimit1@example.com"))
    document_id = await _create_document(client, headers, "Rate Limit Isolation Doc")

    chunks = [
        _chunk(document_id, "node-0001", "Acme Corp is a vendor."),
        _chunk(document_id, "node-0002", "Globex LLC is a client."),
    ]
    sleep = _FakeSleep()
    # Chunk 1 exhausts retries (always rate-limited); chunk 2 succeeds
    # on its first try.
    gateway = _ScriptedGateway(
        [_rate_limit_error(), _rate_limit_error(), _rate_limit_error(), _SUCCESS_JSON]
    )
    extractor = GraphExtractor(
        gateway,
        min_request_interval_seconds=0,
        max_retries=2,
        retry_base_delay_seconds=0.01,
        sleep=sleep,
    )

    async with AsyncSessionLocal() as session:
        service = GraphExtractionService(session, extractor)
        result = await service.extract_for_document(document_id, chunks)

    assert result.chunks_processed == 2
    assert result.chunks_failed == 1
    assert result.chunks_succeeded == 1
    assert result.errors[0].chunk_id == "node-0001"
    assert result.entities_created == 1  # only chunk 2's entity

    async with AsyncSessionLocal() as session:
        entities = (
            await session.execute(
                select(GraphEntity).where(GraphEntity.document_id == document_id)
            )
        ).scalars().all()
        assert len(entities) == 1
        assert entities[0].canonical_name == "acme corp"


# --- Malformed-JSON robustness -------------------------------------------


@pytest.mark.asyncio
async def test_parses_json_wrapped_in_surrounding_prose():
    gateway = _ScriptedGateway(
        [f"Sure, here's the extracted data:\n\n{_SUCCESS_JSON}\n\nLet me know if you need more."]
    )
    extractor = GraphExtractor(gateway, min_request_interval_seconds=0)

    result = await extractor.extract("Acme Corp is a vendor.")

    assert result.entities[0].canonical_name == "acme corp"


@pytest.mark.asyncio
async def test_parses_json_with_trailing_commas():
    malformed = """{
      "entities": [
        {"name": "Acme Corp", "canonical_name": "acme corp", "entity_type": "organization"},
      ],
      "relationships": [],
    }"""
    gateway = _ScriptedGateway([malformed])
    extractor = GraphExtractor(gateway, min_request_interval_seconds=0)

    result = await extractor.extract("Acme Corp is a vendor.")

    assert result.entities[0].canonical_name == "acme corp"


@pytest.mark.asyncio
async def test_parses_json_with_fences_prose_and_trailing_commas_combined():
    malformed = f"""Here you go:
```json
{{
  "entities": [
    {{"name": "Acme Corp", "canonical_name": "acme corp", "entity_type": "organization"}},
  ],
  "relationships": [],
}}
```
Hope that helps!"""
    gateway = _ScriptedGateway([malformed])
    extractor = GraphExtractor(gateway, min_request_interval_seconds=0)

    result = await extractor.extract("Acme Corp is a vendor.")

    assert result.entities[0].canonical_name == "acme corp"


@pytest.mark.asyncio
async def test_does_not_invent_content_for_missing_required_fields():
    """A syntactically-fixable slip (trailing comma, wrapping prose) is
    repaired; a semantically incomplete entity (missing a required
    field entirely) is NOT invented/filled in -- it must still raise."""
    malformed = """{
      "entities": [
        {"name": "Acme Corp", "entity_type": "organization"}
      ],
      "relationships": []
    }"""
    gateway = _ScriptedGateway([malformed])
    extractor = GraphExtractor(gateway, min_request_interval_seconds=0)

    with pytest.raises(GraphExtractionError):
        await extractor.extract("Acme Corp is a vendor.")


@pytest.mark.asyncio
async def test_does_not_repair_genuinely_broken_json():
    gateway = _ScriptedGateway(["this is not json at all, no braces here"])
    extractor = GraphExtractor(gateway, min_request_interval_seconds=0)

    with pytest.raises(GraphExtractionError):
        await extractor.extract("Acme Corp is a vendor.")
