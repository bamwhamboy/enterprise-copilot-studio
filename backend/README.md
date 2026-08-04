# Enterprise Copilot Studio — Backend

FastAPI backend for Enterprise Copilot Studio.

- **Sprint 1 (foundation)**: app skeleton, configuration, logging, `GET /health`.
- **Sprint 2 (persistence)**: PostgreSQL, SQLAlchemy, the repository pattern,
  and CRUD APIs for **Copilot**, **KnowledgeSource**, and **Document**.
- **Sprint 3A (this update)**: the Enterprise Knowledge Engine's
  **ingestion pipeline** — `POST /documents/upload` accepts real PDFs,
  saves them to disk, extracts text and metadata via PyMuPDF, and
  registers everything in PostgreSQL. Still **no retrieval, no AI**: no
  Qdrant, no embeddings, no chunking, no LangGraph, no LiteLLM, no chat,
  no reranking, no citations.

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
│   ├── main.py                     # App factory + 4 exception handlers (was 1)
│   ├── api/
│   │   └── v1/
│   │       ├── health.py
│   │       ├── copilots.py
│   │       ├── knowledge_sources.py
│   │       └── documents.py         # + POST /upload (new)
│   ├── core/
│   │   ├── config.py                # + STORAGE_DIR, MAX_UPLOAD_SIZE_MB (updated)
│   │   ├── dependencies.py          # + storage/pipeline DI providers (updated)
│   │   └── exceptions.py            # + 3 new exception types (updated)
│   ├── knowledge_engine/            # Sprint 3A — new subpackages
│   │   ├── __init__.py               # docstring updated: ingestion implemented, retrieval still future
│   │   ├── storage/
│   │   │   └── document_storage.py   # save / load / delete files on disk
│   │   ├── parser/
│   │   │   └── pdf_parser.py         # PyMuPDF text + page-count extraction
│   │   ├── metadata/
│   │   │   └── extractor.py          # filename / MIME type / size extraction
│   │   └── pipeline/
│   │       └── ingestion_pipeline.py # orchestrates storage + parser + metadata
│   ├── models/
│   │   └── document.py              # + 6 nullable ingestion columns (updated)
│   ├── schemas/
│   │   └── document.py              # DocumentRead + ingestion fields (updated)
│   ├── services/
│   │   └── document_service.py      # + upload_document(), delete cleans up files (updated)
│   ├── repositories/                # Unchanged from Sprint 2
│   ├── database/ middleware/        # Unchanged from Sprint 1
│   └── planner/ memory/ tool_calling/ llm/ guardrails/ utils/   # Still empty placeholders
├── storage/documents/                # Uploaded PDFs + extracted .txt sidecars (gitignored)
├── alembic/versions/
│   └── ..._add_document_ingestion_fields.py   # New migration
├── tests/
│   └── test_document_upload.py      # New — 5 tests, real PDFs via PyMuPDF, no mocking
```



## CRUD & Ingestion Endpoints

All mounted under `/api/v1` (health stays unversioned at `/health`):

| Entity | Endpoints |
|---|---|
| Copilots | `GET /api/v1/copilots`, `GET /{id}`, `POST`, `PUT /{id}`, `DELETE /{id}` |
| Knowledge Sources | `GET /api/v1/knowledge-sources`, `GET /{id}`, `POST`, `PUT /{id}`, `DELETE /{id}` |
| Documents | `GET /api/v1/documents` (optional `?knowledge_source_id=`), `GET /{id}`, `POST` (JSON, no file), **`POST /upload`** (multipart PDF — new), `DELETE /{id}` |

Notes:
- Creating a Copilot accepts `knowledge_source_ids: [...]` to attach existing sources.
- Updating a Copilot with `knowledge_source_ids` **replaces** its full set of linked sources.
- Not-found entities return a clean `404 {"detail": "..."}`, not a raw 500.

## Ingestion Pipeline (Sprint 3A)

`POST /api/v1/documents/upload` accepts `multipart/form-data` with a
`knowledge_source_id` field and a `file` (PDF only), then:

1. Validates the parent `KnowledgeSource` exists (404 if not) and the file is a PDF within `MAX_UPLOAD_SIZE_MB` (415 / 413 if not).
2. Saves the file to `STORAGE_DIR` under a UUID-generated filename.
3. Registers a `Document` row immediately with `processing_status="UPLOADED"`.
4. Transitions to `"PROCESSING"`, extracts text + page count via PyMuPDF (in a worker thread, off the event loop).
5. Saves the extracted text as a `.txt` sidecar file next to the PDF.
6. On success: updates `pages`, `mime_type`, `file_size_bytes`, `extracted_text_path`, sets `processing_status="READY"` and syncs the legacy `status="indexed"`.
7. On parse failure: sets `processing_status="FAILED"` and returns `422` — the row and the saved file remain for debugging.

`DELETE /api/v1/documents/{id}` now also deletes the PDF and its `.txt` sidecar from disk, not just the DB row.

No chunking, no embeddings, no Qdrant, no LLM calls anywhere in this flow.

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
3. Expand **Documents → POST /api/v1/documents/upload**, click *Try it
   out*. This form has two fields:
   - `knowledge_source_id`: paste the id from step 2
   - `file`: click *Choose File* and pick any real PDF from your machine

   Execute it. The response comes back with `processing_status: "READY"`,
   the real extracted `pages` count, `storage_path`, and
   `extracted_text_path`. Copy the returned `id`.
4. Expand **Documents → GET /api/v1/documents/{document_id}**, paste the
   id from step 3, and confirm it round-trips with the same fields.
5. Expand **Copilots → POST /api/v1/copilots**, *Try it out*, and create a
   copilot referencing the knowledge source from step 2:
   ```json
   { "name": "HR Copilot", "domain": "hr", "knowledge_source_ids": ["<paste id>"] }
   ```
   The response embeds the linked knowledge source.
6. Try **GET /api/v1/copilots** and **GET /api/v1/copilots/{copilot_id}** to
   confirm the copilot (and its relationship) round-trips correctly.
7. Try **PUT /api/v1/copilots/{copilot_id}** with `{"status": "active"}` to
   confirm partial updates work and unrelated fields are preserved.
8. Try uploading a **non-PDF file** (e.g. a `.txt`) via
   **POST /api/v1/documents/upload** — confirms the `415` handler.
9. Try **DELETE /api/v1/documents/{document_id}** on the document from step
   3, then **GET** it again — confirms `404`, and check your local
   `storage/documents/` folder to see the PDF and `.txt` sidecar are gone.
10. Try **DELETE /api/v1/knowledge-sources/{knowledge_source_id}** on the
    source from step 2 (create a fresh document under it first if you
    deleted the earlier one) — confirms the cascade delete removes its
    documents too.
11. Try any `GET .../{id}` with a random UUID (e.g.
    `00000000-0000-0000-0000-000000000000`) — confirms the clean 404 handler.

Every step above was run for real — a live PostgreSQL instance, a real
PyMuPDF-generated PDF uploaded over actual HTTP, its extracted text
verified on disk, and files confirmed deleted after a DELETE call — not
just written and assumed to work. The automated suite (`pytest -v`, 32
tests) covers the same ground and was run three times consecutively
with no flakes.

## Sample Upload Request

Using `curl`:

```bash
# 1. Create a knowledge source (or reuse an existing id)
KS_ID=$(curl -s -X POST http://localhost:8000/api/v1/knowledge-sources \
  -H "Content-Type: application/json" \
  -d '{"name": "HR Policies", "source_type": "documents"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

# 2. Upload a PDF into it
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "knowledge_source_id=$KS_ID" \
  -F "file=@/path/to/Employee_Handbook.pdf;type=application/pdf"
```

Response:

```json
{
  "id": "3243f61c-0d72-4a60-ab82-a76c47cac79f",
  "knowledge_source_id": "11c99cbb-e7ae-423d-835b-9d43e19e8370",
  "name": "Employee_Handbook.pdf",
  "status": "indexed",
  "pages": 2,
  "chunks": 0,
  "embeddings": 0,
  "original_filename": "Employee_Handbook.pdf",
  "storage_path": "storage/documents/fb33bbb7-8f8c-4479-ae5e-b54ea7451d8d.pdf",
  "extracted_text_path": "storage/documents/fb33bbb7-8f8c-4479-ae5e-b54ea7451d8d.txt",
  "mime_type": "application/pdf",
  "file_size_bytes": 1323,
  "processing_status": "READY",
  "created_at": "2026-08-04T17:37:02.048186Z",
  "updated_at": "2026-08-04T17:37:02.061490Z"
}
```

(`chunks` and `embeddings` stay `0` — chunking and embedding are
explicitly out of scope for this sprint.)

## Database Migrations (Alembic)

`alembic/env.py` imports `app.models` so `Base.metadata` is fully
populated, and reads the DB URL from `app.core.config.get_settings()` —
no separate configuration needed.

```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
```

## New Dependencies (Sprint 3A)

| Package | Why |
|---|---|
| `python-multipart` | Required by FastAPI/Starlette to parse `multipart/form-data` (file uploads) |
| `pymupdf` (imports as `fitz`) | PDF text extraction and page counting |
| `aiofiles` | Async file writes/reads in the storage service, off the event loop |

## What's Intentionally Not Here

Still not implemented, per scope: Qdrant, embeddings, chunking,
LangGraph, LiteLLM, chat APIs, retrieval, reranking, citations, and
authentication. These land in a future sprint, building on the
documents this one registers and the text it extracts.

