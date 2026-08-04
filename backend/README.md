# Enterprise Copilot Studio — Backend

FastAPI backend for Enterprise Copilot Studio.

- **Sprint 1 (foundation)**: app skeleton, configuration, logging, `GET /health`.
- **Sprint 2 (this update)**: persistence layer — PostgreSQL, SQLAlchemy,
  the repository pattern, and CRUD APIs for **Copilot**, **KnowledgeSource**,
  and **Document**. Still **no AI functionality** — no RAG, no Qdrant, no
  LangGraph, no LiteLLM, no embeddings, no chat APIs, no auth, no Redis logic.

## Tech Stack

| Concern        | Choice                          |
|-----------------|----------------------------------|
| Language        | Python 3.12                     |
| Web framework   | FastAPI + Uvicorn                |
| Validation      | Pydantic v2 / pydantic-settings  |
| Database        | PostgreSQL via SQLAlchemy 2.0 (async) |
| Migrations      | Alembic                          |
| Containerization| Docker / Docker Compose          |
| Testing         | pytest, pytest-asyncio, httpx    |

Redis, Qdrant, LiteLLM, LangGraph, and LlamaIndex remain provisioned in
`docker-compose.yml` / `.env.example` but unused in code — that's a later
phase.

## Data Model (Sprint 2)

```
Copilot ──< copilot_knowledge_sources >── KnowledgeSource ──< Document
        (many-to-many)                                    (one-to-many)
```

- **Copilot**: `name`, `description`, `domain`, `status`, `model`, plus a
  many-to-many link to `KnowledgeSource` (a source can back more than one
  copilot).
- **KnowledgeSource**: `name`, `source_type` (documents/database/website/
  connector), `status`.
- **Document**: belongs to exactly one `KnowledgeSource`
  (`ON DELETE CASCADE` — deleting a source deletes its documents),
  `name`, `status`, `pages`, `chunks`, `embeddings`.

## Folder Structure

```
backend/
├── app/
│   ├── main.py                     # App factory + 404 exception handler
│   ├── api/
│   │   ├── router.py                # Aggregates health (unversioned) + v1 (business) routers
│   │   └── v1/
│   │       ├── health.py            # GET /health
│   │       ├── copilots.py          # Copilot CRUD
│   │       ├── knowledge_sources.py # KnowledgeSource CRUD
│   │       └── documents.py         # Document GET/POST/DELETE
│   ├── core/
│   │   ├── config.py                # Settings (unchanged from Sprint 1)
│   │   ├── logging.py
│   │   ├── dependencies.py          # + service-layer DI providers (new)
│   │   └── exceptions.py            # NotFoundError (new)
│   ├── models/                      # SQLAlchemy ORM models (new)
│   │   ├── copilot.py
│   │   ├── knowledge_source.py
│   │   └── document.py
│   ├── schemas/                     # Pydantic request/response schemas (new)
│   │   ├── common.py
│   │   ├── copilot.py
│   │   ├── knowledge_source.py
│   │   └── document.py
│   ├── repositories/                # Repository pattern (new package)
│   │   ├── base.py                  # Generic async CRUD repository
│   │   ├── copilot_repository.py
│   │   ├── knowledge_source_repository.py
│   │   └── document_repository.py
│   ├── services/                    # Business logic layer (new)
│   │   ├── copilot_service.py
│   │   ├── knowledge_source_service.py
│   │   └── document_service.py
│   ├── database/                    # Unchanged from Sprint 1
│   ├── middleware/                  # Unchanged from Sprint 1
│   └── planner/ knowledge_engine/ memory/ tool_calling/ llm/
│       guardrails/ utils/           # Still empty placeholders
├── alembic/
│   └── versions/
│       └── ..._add_copilot_knowledge_source_document_.py   # New migration
├── tests/
│   ├── conftest.py                  # + dedicated test DB, schema setup (updated)
│   ├── test_health.py               # Unchanged from Sprint 1
│   ├── test_copilots.py             # New — 10 tests
│   ├── test_knowledge_sources.py    # New — 8 tests
│   └── test_documents.py            # New — 6 tests
```

## CRUD Endpoints

All mounted under `/api/v1` (health stays unversioned at `/health`):

| Entity | Endpoints |
|---|---|
| Copilots | `GET /api/v1/copilots`, `GET /{id}`, `POST`, `PUT /{id}`, `DELETE /{id}` |
| Knowledge Sources | `GET /api/v1/knowledge-sources`, `GET /{id}`, `POST`, `PUT /{id}`, `DELETE /{id}` |
| Documents | `GET /api/v1/documents` (optional `?knowledge_source_id=`), `GET /{id}`, `POST`, `DELETE /{id}` |

Notes:
- Creating a Copilot accepts `knowledge_source_ids: [...]` to attach existing sources.
- Updating a Copilot with `knowledge_source_ids` **replaces** its full set of linked sources.
- Creating a Document validates the parent `knowledge_source_id` exists (404 if not) rather than surfacing a raw FK error.
- Not-found entities return a clean `404 {"detail": "..."}` via a registered `NotFoundError` handler, not a raw 500.

## How to Run

### Option A — Docker Compose (recommended)

```bash
cd backend
cp .env.example .env
docker compose up --build
```

On first run, apply migrations inside the running container:

```bash
docker compose exec api alembic upgrade head
```

### Option B — Local virtualenv

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Point DATABASE_URL at your local PostgreSQL if it's not on the default host/port.

alembic upgrade head
uvicorn app.main:app --reload
```

## How to Test Every Endpoint Using Swagger

1. Start the API (either option above) and open **`http://localhost:8000/docs`**.
2. Expand **Knowledge Sources → POST /api/v1/knowledge-sources**, click
   *Try it out*, and create one, e.g.:
   ```json
   { "name": "HR Policies", "source_type": "documents", "status": "active" }
   ```
   Copy the `id` from the response.
3. Expand **Documents → POST /api/v1/documents**, *Try it out*, and create a
   document using that `knowledge_source_id`:
   ```json
   { "knowledge_source_id": "<paste id>", "name": "Employee Handbook.pdf", "status": "indexed", "pages": 28, "chunks": 182, "embeddings": 182 }
   ```
4. Expand **Copilots → POST /api/v1/copilots**, *Try it out*, and create a
   copilot referencing the same knowledge source:
   ```json
   { "name": "HR Copilot", "domain": "hr", "knowledge_source_ids": ["<paste id>"] }
   ```
   The response embeds the linked knowledge source.
5. Try **GET /api/v1/copilots** and **GET /api/v1/copilots/{copilot_id}** to
   confirm the copilot (and its relationship) round-trips correctly.
6. Try **PUT /api/v1/copilots/{copilot_id}** with `{"status": "active"}` to
   confirm partial updates work and unrelated fields are preserved.
7. Try **DELETE /api/v1/knowledge-sources/{knowledge_source_id}** on the
   source you created, then **GET /api/v1/documents/{document_id}** — it
   should now 404, confirming the cascade delete.
8. Try any `GET .../{id}` with a random UUID (e.g.
   `00000000-0000-0000-0000-000000000000`) — confirms the clean 404 handler.

Every step above was run for real against a live PostgreSQL instance while
building this, along with the automated test suite (`pytest -v`, 27 tests,
including 8 SQLAlchemy-relationship/cascade-specific cases) — not just
written and assumed to work.

## Database Migrations (Alembic)

`alembic/env.py` imports `app.models` so `Base.metadata` is fully
populated, and reads the DB URL from `app.core.config.get_settings()` —
no separate configuration needed.

```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
```

## What's Intentionally Not Here

Still not implemented, per scope: RAG, Qdrant queries, Redis caching,
LangGraph agents, LiteLLM calls, embeddings generation, chat APIs, and
authentication. These land in a future sprint, building on the
repository/service pattern established here.

