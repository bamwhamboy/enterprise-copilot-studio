# Enterprise Copilot Studio — backend agent notes

Durable, hard-won knowledge about this codebase. Read this before
exploring from scratch — it exists specifically to avoid re-deriving
things that already took real investigation to figure out once.

## Architecture in one paragraph

FastAPI + SQLAlchemy (async) + PostgreSQL (Supabase in prod) +
Qdrant Cloud (vectors) + LangGraph (chat orchestration) + LiteLLM
(provider-agnostic LLM calls, currently Groq/`openai/gpt-oss-120b`) +
W&B Weave (tracing + response evaluation). Multi-tenant: every table
that matters is organization-scoped.

## Non-obvious but critical: lazy imports in `app/core/dependencies.py`

`litellm` is expensive to import. `dependencies.py` is imported
eagerly at app startup (via router imports), so any module-level
import of `LLMGateway` (or anything that transitively imports it)
there would pay that cost on every single request, even ones that
never touch the LLM. The existing pattern: import inside the provider
function body, deferred to call time, with only a `TYPE_CHECKING`
import for the type hint. `get_llm_gateway`, `get_chat_workflow`, and
`get_graph_extraction_service` all follow this. Keep following it for
anything new that touches an LLM.

`get_graph_extraction_service` also gates on
`settings.GRAPH_EXTRACTION_ENABLED` (default `False`) — this isn't
just a feature flag, it's how the module avoids paying the litellm
import cost at all unless graph extraction is actually turned on.

## Running tests locally

Tests need a real local Postgres — there's no sqlite fallback.

```bash
service postgresql start
su postgres -c "psql -c \"CREATE DATABASE ecs;\""       # dev DB
su postgres -c "psql -c \"CREATE DATABASE ecs_test;\""  # test DB
```

`tests/conftest.py` reads `DATABASE_URL` (defaults to
`postgresql+asyncpg://postgres:postgres@localhost:5432/ecs_test`) and
creates tables via `Base.metadata.create_all` — tests don't run
Alembic migrations, so a new model just needs to be imported in
`app/models/__init__.py` to be picked up.

`app/dependency_overrides` in `conftest.py` globally overrides
`get_embed_model` (→ `MockEmbedding`) and `get_qdrant_client` (→ an
in-memory test client) for the whole suite. No global LLM-gateway
override exists — individual tests that need one either monkeypatch
`litellm.acompletion` directly, or override
`get_graph_extraction_service`/similar per-test and clean up in a
fixture teardown.

```bash
pytest tests/test_whatever.py -v   # focused
pytest -q                           # full suite — currently ~230 tests, ~2 min
```

## Graph RAG (`app/knowledge_engine/graph/`)

- `extractor.py` — one LLM call per chunk, extracts entities +
  relationships as JSON. Has its own rate-limit retry/backoff
  (`litellm.RateLimitError`, honors `Retry-After`) and proactive
  pacing (`min_request_interval_seconds`) because Groq's TPM limit is
  easy to blow through with one call per chunk on a large document.
- `graph_extraction_service.py` — orchestrates per-chunk
  extraction + persistence. **Per-chunk failure isolation is load-
  bearing**: each chunk gets its own local cache/counters, merged into
  shared state only after that chunk's commit succeeds. A chunk that
  fails is rolled back and skipped; it must never poison later
  chunks' entity resolution. If you touch this file, re-read that
  merge-on-success pattern before changing it — it's there because an
  earlier version leaked stale (rolled-back) entity IDs into
  subsequent chunks.
- `canonicalization.py` — `normalize_canonical_name()`, the single
  shared function both `extractor.py` (same-chunk relationship
  validation) and `graph_extraction_service.py` (cross-chunk entity
  resolution) use. Syntactic normalization only (whitespace/case/
  separators) — deliberately never semantic/synonym merging.
- Wired into `IndexingService` additively: a graph extraction failure
  (partial or total) never blocks vector indexing or flips
  `index_status` to `FAILED`. The failure summary (`status`,
  `sample_errors` with real error messages, not just chunk IDs) is
  returned in `IndexDocumentResponse.graph_extraction` — check that
  field first when graph extraction produces zero rows silently;
  don't assume it's a persistence bug without checking.

## Multi-format ingestion (`app/knowledge_engine/parser/`)

`ParserRegistry` resolves a `DocumentParser` by file extension.
Adding a new format = one new parser module (implementing `extract()
-> ParsedDocument`) + one line in `build_default_registry()`. Nothing
downstream of extraction (chunking, Graph RAG, embeddings, Qdrant)
knows or cares which parser produced the text — that boundary is
deliberate and should stay that way.

CSV/XLSX rows are serialized with column names repeated on every row
(`Column: value | Column: value`), not as a markdown table — chunking
is token-based and will split a table at an arbitrary row boundary,
so any format without that repetition loses column context for a
row that ends up in a different chunk than its header.

## Repository / DI conventions

- One file per aggregate in `app/repositories/`, one class per model
  inside it if models are closely related (e.g.
  `conversation_repository.py` holds both session and message
  repos). `find_by_<natural_key>` methods, not generic filters.
- `app/core/dependencies.py` is the only place DI providers live.
  `SettingsDep`, `DbSessionDep` etc. are `Annotated[T, Depends(fn)]`
  aliases — reuse the existing ones rather than declaring a new
  `Depends(get_db_session)` inline.
- New settings go in `app/core/config.py`, grouped with a comment
  header near related settings, with a default that preserves
  existing behavior (new features default off/unchanged unless
  explicitly asked to default on).

## Schema validation conventions

- Free-form fields with sensible bounds (e.g. `Copilot.domain`) are
  validated with a shared `@field_validator`-backed normalization
  function applied identically to both the `*Create` and `*Update`
  schemas, not duplicated logic in each. Length checks apply to the
  *normalized* value when normalization (strip/lowercase) happens,
  matching what the DB column actually stores.

## Working method that's paid off on this repo

- When a bug report says "X should work but produces zero rows /
  empty results," reproduce it with a real fake wired through the
  full DI path before proposing a fix — several apparent "persistence
  bugs" in this repo turned out to be upstream failures (LLM auth,
  rate limits) that were merely invisible, not the persistence code
  being wrong. Check `IndexDocumentResponse.graph_extraction` /
  `sample_errors` first.
- This repo's `main` branch and any patch handed over in a prior
  session are not guaranteed to be in sync — confirm what's actually
  on `origin/main` before assuming a previous fix landed. A merge to
  `main` is also not guaranteed to include every file from a prior
  patch verbatim (e.g. a test-file fix can go missing even when the
  matching implementation change lands) — re-run the full suite
  before trusting that a prior session's fix is actually present.
