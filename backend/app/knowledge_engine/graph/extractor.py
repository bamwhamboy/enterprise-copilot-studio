"""Per-chunk entity/relationship extraction via the existing LLM gateway.

Deliberately thin: this module's only job is "chunk text in, parsed
``ChunkExtractionResult`` out (or raise)". Entity resolution across
chunks, persistence, provenance, and per-chunk failure isolation all
live in ``graph_extraction_service.py`` -- this module has no
knowledge of the database.

Rate-limit handling lives here too, since it's a property of "how we
talk to the LLM for extraction", not of persistence. Groq's TPM
(tokens-per-minute) limit is easy to exceed with one call per chunk on
a multi-hundred-chunk document (e.g. 184 chunks), so this module both
paces its own outgoing calls (a minimum interval + a concurrency cap,
both configurable) and retries reactively on ``litellm.RateLimitError``,
honoring the provider's ``Retry-After`` when it sends one. Neither of
these changes anything about *how* extraction results get used --
GraphExtractionService's per-chunk isolation is untouched; a chunk that
exhausts its retries still fails only that one chunk.
"""

from __future__ import annotations

import asyncio
import json
import random
import re
import time
from collections.abc import Awaitable, Callable

import litellm
from pydantic import ValidationError

from app.core.logging import get_logger
from app.knowledge_engine.graph.models import ChunkExtractionResult
from app.llm.gateway import LLMGateway
from app.llm.models import GenerationRequest, GenerationResponse, LLMMessage

logger = get_logger(__name__)

_SYSTEM_PROMPT = """You are an information-extraction engine for an enterprise \
knowledge graph. Given a single chunk of text from a business document, extract:

1. entities: distinct people, organizations, defined terms, monetary amounts, \
dates, or clauses that matter for understanding the document.
2. relationships: directed relationships between two of the entities you extracted.

Respond with ONLY a single JSON object, no markdown fences, no commentary, in \
exactly this shape:

{
  "entities": [
    {"name": "<surface form as it appears in the text>", \
"canonical_name": "<normalized/lowercased form>", "entity_type": "<short type, \
e.g. organization, person, term, amount, date, clause>"}
  ],
  "relationships": [
    {"source_entity": "<canonical_name of an entity above>", \
"target_entity": "<canonical_name of a different entity above>", \
"relationship_type": "<short snake_case predicate, e.g. provides_services_to>", \
"confidence": <float between 0.0 and 1.0>}
  ]
}

Every "source_entity"/"target_entity" value MUST exactly match a "canonical_name" \
already present in "entities". If the chunk contains no meaningful entities or \
relationships, return {"entities": [], "relationships": []}."""

_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)
_TRAILING_COMMA_RE = re.compile(r",\s*([}\]])")

# Conservative starting points for an 8,000 TPM Groq limit with one call
# per chunk -- tune these against your account's actual measured
# tokens/call rather than treating them as exact. The retry/backoff
# layer below is the safety net for whatever proactive pacing doesn't
# fully cover.
DEFAULT_MAX_CONCURRENCY = 1
DEFAULT_MIN_REQUEST_INTERVAL_SECONDS = 3.0
DEFAULT_MAX_RETRIES = 5
DEFAULT_RETRY_BASE_DELAY_SECONDS = 2.0
DEFAULT_RETRY_MAX_DELAY_SECONDS = 60.0


class GraphExtractionError(Exception):
    """Raised when the LLM response cannot be parsed into a valid
    ``ChunkExtractionResult`` -- covers both malformed JSON and JSON
    that doesn't match the expected schema."""


class GraphExtractionRateLimitError(Exception):
    """Raised when a chunk exhausts its rate-limit retry budget.

    Distinct from ``GraphExtractionError`` (a parsing problem) so
    callers/logs/tests can tell "the model responded but we couldn't
    parse it" apart from "we never got a response because Groq kept
    rate-limiting us" -- both are still plain chunk failures as far as
    GraphExtractionService's per-chunk isolation is concerned.
    """


def _extract_json_object(text: str) -> str:
    """If ``text`` has prose before/after a JSON object (e.g. "Here is
    the JSON: {...}"), return just the outermost balanced ``{...}``.
    Returns ``text`` unchanged if no balanced object is found -- this
    never fabricates or edits content, only narrows to the object that
    was actually there. Tracks string literals so braces inside a
    quoted value don't throw off the balance count.
    """
    start = text.find("{")
    if start == -1:
        return text

    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        char = text[i]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return text


def _strip_trailing_commas(text: str) -> str:
    """Removes a trailing comma directly before ``}``/``]`` -- a common
    LLM JSON slip. Purely syntactic; never touches what's between the
    delimiters.
    """
    return _TRAILING_COMMA_RE.sub(r"\1", text)


class GraphExtractor:
    """Extracts entities and relationships from one chunk of text at a time."""

    def __init__(
        self,
        gateway: LLMGateway,
        *,
        max_concurrency: int = DEFAULT_MAX_CONCURRENCY,
        min_request_interval_seconds: float = DEFAULT_MIN_REQUEST_INTERVAL_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_base_delay_seconds: float = DEFAULT_RETRY_BASE_DELAY_SECONDS,
        retry_max_delay_seconds: float = DEFAULT_RETRY_MAX_DELAY_SECONDS,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        # No Settings object needed here: the gateway already resolves
        # provider/model from Settings.DEFAULT_LLM_PROVIDER /
        # Settings.DEFAULT_LLM_MODEL when a request omits them -- callers
        # (app/core/dependencies.py) read the rate-limit knobs out of
        # Settings themselves and pass plain numbers in here, keeping
        # this class Settings-agnostic and easy to unit test.
        self._gateway = gateway
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._min_request_interval_seconds = min_request_interval_seconds
        self._max_retries = max_retries
        self._retry_base_delay_seconds = retry_base_delay_seconds
        self._retry_max_delay_seconds = retry_max_delay_seconds
        self._sleep = sleep
        # Guards read-modify-write of _last_call_started_at so pacing is
        # correct even if max_concurrency > 1.
        self._pacing_lock = asyncio.Lock()
        self._last_call_started_at: float | None = None

    async def extract(self, chunk_text: str) -> ChunkExtractionResult:
        """Extract entities/relationships from a single chunk's text.

        Raises ``GraphExtractionError`` if the LLM's response cannot be
        parsed, or ``GraphExtractionRateLimitError`` if every retry
        attempt was rate-limited -- callers (``GraphExtractionService``)
        are expected to catch either per chunk rather than let it abort
        the whole document.
        """
        request = GenerationRequest(
            messages=[
                LLMMessage(role="system", content=_SYSTEM_PROMPT),
                LLMMessage(role="user", content=chunk_text),
            ],
            # Deterministic, low-temperature extraction -- this is a
            # structured-data task, not a creative one.
            temperature=0.0,
        )
        response = await self._generate_with_retry(request)
        return self._parse(response.content)

    async def _generate_with_retry(self, request: GenerationRequest) -> GenerationResponse:
        async with self._semaphore:
            attempt = 0
            while True:
                await self._wait_for_pacing_slot()
                try:
                    return await self._gateway.generate(request)
                except litellm.RateLimitError as exc:
                    attempt += 1
                    if attempt > self._max_retries:
                        raise GraphExtractionRateLimitError(
                            f"Exhausted {self._max_retries} retries on Groq "
                            f"rate limiting: {exc}"
                        ) from exc
                    delay = self._retry_delay_seconds(exc, attempt)
                    logger.warning(
                        "Groq rate limit hit (attempt %d/%d); retrying in "
                        "%.1fs",
                        attempt,
                        self._max_retries,
                        delay,
                    )
                    await self._sleep(delay)

    async def _wait_for_pacing_slot(self) -> None:
        """Proactive pacing: sleep as needed so calls are spaced at
        least ``min_request_interval_seconds`` apart, regardless of how
        fast the caller loops over chunks. This is what actually keeps
        184 sequential chunks from firing "as fast as possible" -- the
        retry logic above is the reactive fallback for whatever this
        doesn't fully prevent.
        """
        async with self._pacing_lock:
            now = time.monotonic()
            if self._last_call_started_at is not None:
                elapsed = now - self._last_call_started_at
                remaining = self._min_request_interval_seconds - elapsed
                if remaining > 0:
                    await self._sleep(remaining)
            self._last_call_started_at = time.monotonic()

    def _retry_delay_seconds(self, exc: litellm.RateLimitError, attempt: int) -> float:
        retry_after = self._extract_retry_after(exc)
        if retry_after is not None:
            return min(retry_after, self._retry_max_delay_seconds)

        # No Retry-After given -- exponential backoff with a little
        # jitter so retries from multiple chunks don't all land on the
        # exact same instant.
        backoff = self._retry_base_delay_seconds * (2 ** (attempt - 1))
        jitter = backoff * 0.1 * random.random()
        return min(backoff + jitter, self._retry_max_delay_seconds)

    @staticmethod
    def _extract_retry_after(exc: litellm.RateLimitError) -> float | None:
        """Reads Retry-After from wherever litellm/openai actually put
        it -- exc.headers is populated directly on the exception in
        practice, but fall back to exc.response.headers since that's
        the more "standard" httpx location if a future litellm version
        stops setting .headers directly.
        """
        headers = getattr(exc, "headers", None)
        if not headers:
            response = getattr(exc, "response", None)
            headers = getattr(response, "headers", None) if response is not None else None
        if not headers:
            return None

        for key in ("retry-after", "Retry-After"):
            value = headers.get(key) if hasattr(headers, "get") else None
            if value is not None:
                try:
                    return float(value)
                except (TypeError, ValueError):
                    continue
        return None

    def _parse(self, raw_content: str) -> ChunkExtractionResult:
        cleaned = _JSON_FENCE_RE.sub("", raw_content.strip()).strip()
        cleaned = _extract_json_object(cleaned)
        cleaned = _strip_trailing_commas(cleaned)

        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise GraphExtractionError(
                f"LLM response was not valid JSON: {exc}"
            ) from exc

        try:
            result = ChunkExtractionResult.model_validate(payload)
        except ValidationError as exc:
            raise GraphExtractionError(
                f"LLM response did not match the expected extraction schema: {exc}"
            ) from exc

        known_canonical_names = {entity.canonical_name for entity in result.entities}
        valid_relationships = []
        for relationship in result.relationships:
            if (
                relationship.source_entity not in known_canonical_names
                or relationship.target_entity not in known_canonical_names
            ):
                logger.warning(
                    "Dropping relationship referencing unknown entity "
                    "(source=%r target=%r); not present in this chunk's "
                    "extracted entities",
                    relationship.source_entity,
                    relationship.target_entity,
                )
                continue
            valid_relationships.append(relationship)

        return ChunkExtractionResult(
            entities=result.entities, relationships=valid_relationships
        )
