# Enterprise Copilot Studio — Backend

Foundation-phase FastAPI backend for Enterprise Copilot Studio. This phase
establishes a clean, modular, production-ready service skeleton — **no AI
functionality is implemented yet**. The only route is `GET /health`.

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

Redis, Qdrant, LiteLLM, LangGraph, and LlamaIndex are part of the
platform's intended stack and are **provisioned in `docker-compose.yml`**
and **configured in `.env.example`**, but no application code connects to
or calls them yet — that arrives in the AI-services phase.

## Folder Structure

```
backend/
├── app/
│   ├── main.py                # FastAPI app factory + entrypoint
│   ├── api/
│   │   ├── router.py           # Aggregates all sub-routers
│   │   └── v1/
│   │       └── health.py       # GET /health — the only route in this phase
│   ├── core/
│   │   ├── config.py           # Pydantic v2 Settings (single source of truth)
│   │   ├── logging.py          # Structured logging setup
│   │   └── dependencies.py     # Shared DI providers
│   ├── middleware/
│   │   └── request_context.py  # Request ID + request/response logging
│   ├── database/
│   │   ├── base.py             # SQLAlchemy declarative base
│   │   └── session.py          # Async engine, session factory, get_db()
│   ├── schemas/
│   │   └── health.py           # Pydantic response models
│   ├── planner/                # (placeholder) LangGraph agent orchestration
│   ├── knowledge_engine/       # (placeholder) Hierarchical Hybrid RAG
│   ├── memory/                 # (placeholder) conversation/context memory
│   ├── tool_calling/           # (placeholder) structured tool invocation
│   ├── llm/                    # (placeholder) LiteLLM gateway + routing
│   ├── guardrails/             # (placeholder) prompt sanitization, PII, policy
│   ├── models/                 # (placeholder) SQLAlchemy ORM models
│   ├── services/               # (placeholder) business logic layer
│   └── utils/                  # (placeholder) shared helpers
├── alembic/                    # Migration environment (wired to app Settings + Base)
├── tests/
│   ├── conftest.py             # Async test client fixture
│   └── test_health.py          # Tests for GET /health
├── Dockerfile                  # Multi-stage, non-root runtime image
├── docker-compose.yml          # api + postgres + redis + qdrant
├── requirements.txt
├── .env.example
├── alembic.ini
└── pytest.ini
```

The nine placeholder packages (`planner/`, `knowledge_engine/`, `memory/`,
`tool_calling/`, `llm/`, `guardrails/`, `models/`, `services/`, `utils/`)
contain only a docstring each. They exist so later phases add code to an
already-agreed module boundary instead of restructuring the app.

## How to Run

### Option A — Docker Compose (recommended)

Brings up the API alongside Postgres, Redis, and Qdrant:

```bash
cd backend
cp .env.example .env
docker compose up --build
```

The API will be available at `http://localhost:8000`, with hot-reload
enabled (the local directory is volume-mounted into the container).

- Health check: `http://localhost:8000/health`
- Interactive docs: `http://localhost:8000/docs`

### Option B — Local virtualenv

Requires a locally running PostgreSQL instance if you want the database
session to actually connect (not required for `/health`, which has no
database dependency).

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env if your local Postgres isn't on the default host/port.

uvicorn app.main:app --reload
```

## How to Test

```bash
cd backend
source .venv/bin/activate   # if not already active
pytest -v
```

Tests run against the app in-process via `httpx.ASGITransport` — no
running server, database, Redis, or Qdrant instance is required. This
was verified in a real virtualenv during development: dependencies
install cleanly, the app boots, and all tests pass.

## Database Migrations (Alembic)

No models exist yet, so there's nothing to migrate. Once models are
added under `app/models/` (inheriting from `app.database.base.Base`),
generate a migration with:

```bash
alembic revision --autogenerate -m "add <table>"
alembic upgrade head
```

`alembic/env.py` is already wired to `app.core.config.get_settings()` and
`app.database.base.Base.metadata`, so this will work without further
configuration once real models exist.

## What's Intentionally Not Here

Per this phase's scope, the following are **not implemented**: RAG,
Qdrant queries, Redis caching, LangGraph agents, LiteLLM calls,
embeddings, any LLM calls, document parsing, or any API route beyond
`GET /health`. These land in the next phase, building on the module
boundaries already established here.
