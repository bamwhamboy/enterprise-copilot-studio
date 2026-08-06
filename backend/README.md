# Enterprise Copilot Studio — Backend

FastAPI backend for Enterprise Copilot Studio.

- **Sprint 1 (foundation)**: app skeleton, configuration, logging, `GET /health`.
- **Sprint 2 (persistence)**: PostgreSQL, SQLAlchemy, the repository pattern,
  and CRUD APIs for **Copilot**, **KnowledgeSource**, and **Document**.
- **Sprint 3A (ingestion)**: the Enterprise Knowledge Engine's
  **ingestion pipeline** — `POST /documents/upload` accepts real PDFs,
  saves them to disk, extracts text and metadata via PyMuPDF, and
  registers everything in PostgreSQL.
- **Sprint 4 (AI infrastructure)**: the AI infrastructure future RAG and
  Copilot implementations sit on — an LLM Gateway with a real
  provider-routing layer, a Planner interface, a Guardrails validation
  framework, a Prompt Engine, and Correlation ID propagation.
- **Sprint 3B (retrieval)**: the **Enterprise Retrieval Engine** —
  hierarchical chunking, embeddings, indexing into Qdrant, and hybrid
  (semantic + BM25) retrieval with citation-preserving context
  compression.
- **Sprint 5 (chat runtime)**: LangGraph orchestrates a 5-node workflow
  (planner → retrieval → context builder → response generator →
  citation builder); the LLM Gateway is completed with real LiteLLM
  calls across 5 providers; conversation memory, a guardrails runtime,
  a tool-calling framework, and RAG improvements are all wired
  together behind `POST /api/v1/chat` and `POST /api/v1/chat/stream`.
- **Sprint 6 (this update)**: **Authentication & Authorization** —
  JWT-based auth (bcrypt password hashing, access/refresh tokens with
  rotation and revocation), 5-role RBAC seeded via migration,
  multi-tenancy (Organization scoping), and `/chat` now derives the
  authenticated user's identity automatically instead of trusting a
  client-supplied `user_id`.

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

## AI Infrastructure (Sprint 4)

The architecture future RAG (Sprint 3B) and multi-provider Copilot chat
(Sprint 5) will be built on. **Nothing here makes a network call or an
LLM API call** — this sprint builds routing, interfaces, and
configuration only.

```
app/
├── llm/
│   ├── models.py       # LLMProvider enum, LLMMessage, GenerationRequest/Response,
│   │                    # StreamChunk, ProviderHealth — shared, strongly-typed contracts
│   ├── providers.py     # BaseLLMProviderClient interface + one stub client per
│   │                    # provider (OpenAI/Groq/Azure OpenAI/Anthropic). health() is
│   │                    # real (reports config readiness); generate()/stream() raise
│   │                    # NotImplementedError — no API calls anywhere.
│   └── gateway.py       # LLMGateway — REAL provider/model selection + routing logic,
│                         # delegates to the resolved provider client
├── planner/
│   ├── task.py          # Task model (id, status, depends_on — enough for a DAG)
│   └── planner.py       # Planner ABC (plan()/execute()) — pure interface, no
│                         # concrete implementation, no LangGraph
├── guardrails/
│   ├── validator.py      # ValidationResult/ValidationSeverity + InputValidator/
│   │                      # OutputValidator interfaces
│   └── prompt_sanitizer.py  # PromptSanitizer — REAL rule-based blocked-phrase
│                             # detection; PromptInjectionDetector/PIIDetector are
│                             # interfaces, composed in via constructor injection
├── prompt_engine/          # New package
│   ├── templates.py      # PromptTemplate (system/developer/user) + a small
│   │                      # built-in library
│   └── renderer.py        # PromptRenderer — REAL string-template rendering,
│                           # raises MissingPromptVariableError on incomplete input
└── middleware/
    ├── correlation.py     # New — Correlation ID contextvar + header propagation
    └── request_context.py # Extended (not rewritten) — Sprint 1's Request ID +
                            # timing + X-Request-ID header are unchanged; now also
                            # sets a request_id contextvar and resolves/propagates
                            # the Correlation ID via X-Correlation-ID
```

`app/core/logging.py` was extended with a `_ContextFilter` that reads
both contextvars and injects `request_id`/`correlation_id` into **every**
log line automatically — "structured logging context" without any call
site needing to pass them explicitly. (A deferred, call-time import
inside the filter avoids a circular import with `request_context.py`,
which already imports `get_logger` from this same module.)

`app/core/config.py` gained `DEFAULT_LLM_PROVIDER`, `DEFAULT_LLM_MODEL`,
`DEFAULT_TEMPERATURE`, `DEFAULT_MAX_TOKENS`, and credentials for all four
providers (`ANTHROPIC_API_KEY`, `AZURE_OPENAI_API_KEY`,
`AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_VERSION` — `GROQ_API_KEY`/
`OPENAI_API_KEY` already existed from Sprint 1).

`app/core/dependencies.py` gained `LLMGatewayDep`, `PromptSanitizerDep`,
and `PromptRendererDep` — not consumed by any route yet (no chat/RAG
endpoints exist), but ready for Sprint 3B/5 to `Depends(...)` on, exactly
like every existing service in this file.

### How this gets used by Sprint 3B and Sprint 5

- **Sprint 3B (retrieval / RAG)** will read documents this sprint's
  ingestion pipeline registered, chunk and embed them (new modules
  under `knowledge_engine/`), and use **`PromptRenderer`** to assemble
  the retrieved context into a `GenerationRequest` — without touching
  `llm/` or `guardrails/` at all, since those interfaces are already
  stable.
- **Sprint 5 (copilot chat)** will implement concrete
  `generate()`/`stream()` methods on the provider clients in
  `providers.py` (turning the `NotImplementedError` stubs into real API
  calls), implement a concrete `Planner` (`app/planner/planner.py`) —
  likely LangGraph-based — that produces `Task`s and calls `LLMGateway`
  to execute them, and implement real `PromptInjectionDetector`/
  `PIIDetector` classes that plug into the *existing*
  `PromptSanitizer(injection_detector=..., pii_detector=...)`
  constructor with no changes to `PromptSanitizer` itself.
- In both cases, a new chat/RAG router will `Depends(LLMGatewayDep)`,
  `Depends(PromptSanitizerDep)`, and `Depends(PromptRendererDep)` — the
  DI wiring this sprint added is what makes that a same-pattern,
  low-friction addition rather than new plumbing.

## Enterprise Retrieval Engine (Sprint 3B)

Real, working RAG infrastructure built primarily on LlamaIndex, verified
end to end against real (in-memory) Qdrant and PyMuPDF-generated PDFs.
**One caveat**: this sandbox has no network access to `huggingface.co`,
so the real `BAAI/bge-small-en-v1.5` embedding model can't be downloaded
here — the code path is real (`app/knowledge_engine/embeddings/embedding_model.py`
builds the actual `HuggingFaceEmbedding`), but everything was verified
using LlamaIndex's `MockEmbedding` (identical interface, no network) so
the pipeline mechanics — chunking, indexing, hybrid retrieval, fusion,
compression, citations — are proven correct; only embedding *quality*
is unverified in this environment.

```
app/knowledge_engine/
├── models.py              # ChunkMetadata, HierarchicalChunk, Citation, RetrievedChunk
├── chunking/
│   └── hierarchical_chunker.py   # HierarchicalNodeParser-based chunker (Document ->
│                                   # Section -> Subsection -> Paragraph, parent-child
│                                   # relationships preserved)
├── embeddings/
│   └── embedding_model.py         # HuggingFaceEmbedding factory (BAAI/bge-small-en-v1.5)
├── indexing/
│   ├── vector_store.py            # QdrantClient + QdrantVectorStore wiring
│   └── indexing_service.py        # chunk -> embed -> store -> update Postgres status
├── retrieval/
│   └── hybrid_retriever.py        # semantic (Qdrant) + BM25, fused via RRF
├── compression/
│   └── compression_service.py     # top-N selection + per-chunk truncation, citations preserved
└── citations/
    └── citation_builder.py        # NodeWithScore -> Citation/RetrievedChunk
```

### A real bug found and fixed during development

LlamaIndex's internal `node_to_metadata_dict` (used whenever a node is
written to *any* vector store) unconditionally overwrites a
`"document_id"` metadata key with `node.ref_doc_id` — legacy
Chroma/Pinecone/Qdrant compatibility code. Since our nodes have no
`ref_doc_id` set, this silently clobbered our real document id with the
literal string `"None"`, breaking `GET /chunks/{document_id}`'s filter.
Fixed by storing our field as `source_document_id` instead — see
`indexing_service.py`'s `_chunk_to_node`.

### Hierarchical chunking without NLTK

`HierarchicalNodeParser`'s default per-level splitter (`SentenceSplitter`)
needs NLTK's `punkt` tokenizer data, downloaded at runtime — blocked in
this sandbox (no network to nltk's data servers). Swapped in
`TokenTextSplitter` (tiktoken-based, fully offline) via
`node_parser_map`/`node_parser_ids`, which — note — must be passed
*together*; passing `node_parser_map` alongside `chunk_sizes` instead of
`node_parser_ids` silently ignores the custom map.

### Qdrant Collection Schema

Collection: `knowledge_chunks` (configurable via `QDRANT_COLLECTION_NAME`)

| Field | Type | Notes |
|---|---|---|
| vector | `float[384]`, cosine distance | from `BAAI/bge-small-en-v1.5` (`EMBEDDING_DIMENSION`) |
| `text` (via `_node_content`) | string | chunk text, stored in LlamaIndex's serialized node payload |
| `source_document_id` | string (UUID) | renamed from `document_id` — see bug note above |
| `knowledge_source_id` | string (UUID) | filterable — used by both search and BM25 corpus scoping |
| `document_name` | string | original filename |
| `page_number`, `section`, `subsection` | string/int, nullable | not populated by plain-text extraction (see below) |
| `chunk_number` | int | position within the document |
| `created_at` | ISO datetime string | |

Confirmed via `client.get_collection("knowledge_chunks").config.params.vectors`:
`size=384 distance=Distance.COSINE`.

**Note on `page_number`/`section`/`subsection`**: these are part of every
chunk's metadata shape but are `None` in this sprint — PDF text
extraction (Sprint 3A, PyMuPDF) produces plain text with no layout
information, so section/subsection/page boundaries aren't derivable
without a layout-aware parser. The fields exist now so a future,
layout-aware ingestion path can populate them without changing this
shape or any downstream consumer (search results, citations).

### API

| Endpoint | Description |
|---|---|
| `POST /api/v1/index/{document_id}` | Index a `READY` (parsed) document: chunk, embed, store, update status |
| `GET /api/v1/search?q=...` | Hybrid search — optional `knowledge_source_id`, `top_k` |
| `GET /api/v1/chunks/{document_id}` | List all indexed chunks for a document |

Indexing a document requires `processing_status == "READY"` (set by
Sprint 3A's ingestion pipeline) — indexing a not-yet-parsed or
JSON-created (no file) document returns `409 Conflict`.

### Example Search Request

```bash
curl "http://localhost:8000/api/v1/search?q=How%20many%20leave%20days%20do%20employees%20get&knowledge_source_id=<uuid>&top_k=5"
```

Response:

```json
{
  "query": "How many leave days do employees get",
  "results": [
    {
      "text": "Employees receive 20 days of paid annual leave per year.",
      "score": 0.0328,
      "chunk_id": "06f81744-bcd5-4f5a-bc8a-96a78a376fb8",
      "citation": {
        "document_name": "leave_policy.pdf",
        "knowledge_source_id": "11c99cbb-e7ae-423d-835b-9d43e19e8370",
        "page_number": null,
        "section": null,
        "chunk_number": 0,
        "score": 0.0328
      }
    }
  ]
}
```

### How to Test

```bash
cd backend
pip install -r requirements.txt
pytest tests/test_rag_pipeline.py -v
```

8 tests cover: index → search → chunks round-tripping, a 409 on
not-ready documents, 404 on missing documents, empty-result handling
when nothing's indexed yet, citation correctness, and
`knowledge_source_id` filtering. All run against real (in-memory)
Qdrant with `MockEmbedding` — see `tests/conftest.py`'s
`app.dependency_overrides`. In an environment with network access to
huggingface.co, remove those overrides to test against the real
embedding model.

## Enterprise AI Runtime (Sprint 5)

The chat runtime: LangGraph orchestration, a completed (LiteLLM-backed)
LLM Gateway, conversation memory, a guardrails runtime, tool calling,
and RAG improvements — all tied together by the Chat Orchestrator
behind `POST /api/v1/chat`.

```
app/
├── agents/                       # LangGraph workflow nodes
│   ├── state.py                    # ChatState (shared across the graph)
│   ├── planner_node.py             # + SimpleChatPlanner, first concrete Planner impl
│   ├── retrieval_node.py           # query rewrite -> hybrid retrieval -> rerank -> confidence
│   ├── context_builder_node.py     # assembles system + context + history + user messages
│   ├── response_generator_node.py  # calls LLM Gateway, enforces output guardrails
│   └── citation_builder_node.py    # extracts citations from retrieved chunks
├── workflows/
│   └── chat_workflow.py          # compiles the 5 nodes into a LangGraph StateGraph
├── memory/
│   └── conversation_memory_service.py  # session get-or-create (isolated by user+copilot),
│                                          windowed history load, message append
├── models/
│   └── conversation.py           # ConversationSession, ConversationMessage (Postgres)
├── tool_calling/
│   ├── base.py                     # Tool interface + ToolResult
│   ├── registry.py                 # ToolRegistry
│   └── tools/knowledge_search_tool.py  # wraps HybridRetriever as a callable tool
├── guardrails/
│   ├── pii_detector.py             # RegexPIIDetector: detect() + mask()
│   ├── injection_detector.py       # RegexPromptInjectionDetector (injection + jailbreak)
│   ├── harmful_content_detector.py # HarmfulContentValidator (OutputValidator impl)
│   └── guardrails_runtime.py       # GuardrailsRuntime — the two enforcement checkpoints
├── knowledge_engine/retrieval/     # additive to Sprint 3B, HybridRetriever untouched
│   ├── query_rewriter.py           # rule-based (default) + optional LLM-based rewrite
│   ├── reranker.py                 # lexical-overlap blend over the RRF score
│   └── confidence_scorer.py        # 0-1 confidence from top-score + score-gap
├── llm/
│   └── providers.py               # REWRITTEN IN PLACE: generate()/stream() now call
│                                     # litellm.acompletion for real (5 providers incl. Ollama)
├── services/
│   └── chat_orchestrator.py       # ChatOrchestratorService — the single chat entry point
├── schemas/chat.py, conversation.py
├── repositories/conversation_repository.py
└── api/v1/chat.py                 # POST /chat, POST /chat/stream (SSE)
```

### Architecture: how a chat turn flows

1. **Guardrails (input)** — `GuardrailsRuntime.enforce_input()`: blocked-term list, prompt
   injection/jailbreak patterns (regex-based), PII flagged as a warning (not blocking).
2. **Chat Orchestrator** resolves the copilot, gets-or-creates the conversation session
   (isolated by `user_id` + `copilot_id`), loads windowed history.
3. **LangGraph workflow** runs: `planner` → `retrieval` (query rewrite, hybrid search,
   re-rank, confidence score) → `context_builder` (Prompt Engine renders system + context +
   history + user message) → `response_generator` (LLM Gateway → LiteLLM) →
   `citation_builder`.
4. **Guardrails (output)** — `GuardrailsRuntime.enforce_output()`: harmful-content check,
   then PII masking on the response text.
5. Both turns (user + assistant) are persisted to `ConversationMessage`; the response
   (message, citations, confidence) goes back to the caller.

Streaming (`/chat/stream`) runs steps 1–3's non-LLM parts synchronously, then streams the
LLM response token-by-token via SSE. **Known tradeoff**: output guardrail validation/PII
masking need the complete text (a masked span could straddle a chunk boundary), so they run
once on the full accumulated response in the final `done` event — raw deltas stream
unmasked. The frontend should treat the `done` event's `message` field as authoritative.

### LiteLLM: provider-agnostic by design

`to_litellm_model(provider, model)` is the *only* place that knows a provider's LiteLLM
prefix (`groq/`, `azure/`, `anthropic/`, `ollama/`, none for OpenAI). Switching providers or
models is a `DEFAULT_LLM_PROVIDER`/`DEFAULT_LLM_MODEL` config change — no code changes
anywhere else. Verified via 15 tests in `test_llm_gateway.py`, including a real network call
to Ollama (no API key needed) confirming the integration reaches LiteLLM's actual HTTP layer.

### Extensibility points (built in, not bolted on)

- **Guardrails**: `PromptInjectionDetector`/`PIIDetector`/`OutputValidator` are Sprint 4
  interfaces; Sprint 5's regex-based implementations can be swapped for NVIDIA NeMo
  Guardrails (or any ML-based detector) by implementing the same interfaces and passing them
  into `GuardrailsRuntime`'s constructor — zero changes to the runtime or `ChatOrchestratorService`.
- **Planner**: `SimpleChatPlanner` is the first concrete `Planner` (Sprint 4 interface). A
  smarter planner (e.g. one that chooses between retrieval, tool calls, or a direct answer)
  implements the same `plan()`/`execute()` contract.
- **Tools**: adding SQL/REST/calculator/web-search tools means implementing `Tool` and
  registering it in `get_tool_registry()` — the registry, LangGraph, and orchestrator need
  no changes.
- **Memory**: `ConversationMemoryService`'s public methods are the long-term-memory seam —
  a future summarization/vector-indexed-history method can sit alongside `load_history()`
  without changing its signature or any caller.

### How to Test

**1. Start the stack** (Docker, per the constraints of this sprint — unchanged):
```bash
cd backend
docker compose up --build
docker compose exec api alembic upgrade head
```

**2. Swagger sequence** at `http://localhost:8000/docs`:
1. `POST /api/v1/knowledge-sources` — create one (e.g. `{"name": "HR Policies"}`)
2. `POST /api/v1/documents/upload` — upload a real PDF with that `knowledge_source_id`
3. `POST /api/v1/index/{document_id}` — index it
4. `POST /api/v1/copilots` — create a copilot with `knowledge_source_ids: [<id from step 1>]`
5. `POST /api/v1/chat` — chat against it (sample request below)
6. `POST /api/v1/chat/stream` — same payload, watch the SSE stream in the response body

**3. Sample chat request:**
```json
POST /api/v1/chat
{
  "copilot_id": "11c99cbb-e7ae-423d-835b-9d43e19e8370",
  "user_id": "vijay",
  "message": "How many annual leave days do I get?"
}
```

**Expected response:**
```json
{
  "session_id": "3243f61c-0d72-4a60-ab82-a76c47cac79f",
  "message": "You get 20 days of paid annual leave per year.",
  "citations": [
    {
      "document_name": "leave_policy.pdf",
      "knowledge_source_id": "11c99cbb-e7ae-423d-835b-9d43e19e8370",
      "page_number": null,
      "section": null,
      "chunk_number": 0,
      "score": 0.0328
    }
  ],
  "confidence": 0.81
}
```
Send a follow-up with the returned `session_id` to continue the same conversation.

**4. Validation checklist** (all covered by `pytest`, `tests/test_chat.py` +
`tests/test_llm_gateway.py` + `tests/test_guardrails_runtime.py` + `tests/test_memory.py`):
- **LangGraph**: `test_chat_returns_grounded_response_with_citations` exercises the full
  5-node graph.
- **LiteLLM**: `test_gateway_generate_routes_to_default_provider` (monkeypatched) +
  `test_ollama_reaches_real_litellm_network_layer` (real network layer, no mock).
- **Memory**: `test_session_isolation_by_user_and_copilot`,
  `test_history_is_windowed_to_max_messages`.
- **Guardrails**: `test_chat_rejects_prompt_injection_with_400`,
  `test_chat_masks_pii_in_response`.
- **Streaming**: `test_chat_stream_yields_sse_events` — parses real SSE frames.
- **End-to-end**: `test_chat_session_persists_and_reuses_history` — two turns, same session.

```bash
cd backend
pip install -r requirements.txt
pytest tests/test_chat.py tests/test_llm_gateway.py tests/test_guardrails_runtime.py \
       tests/test_memory.py tests/test_tool_calling.py tests/test_rag_improvements.py -v
```

**Honest limitation**: no real LLM provider API key is available in this development
environment, so every test above monkeypatches `litellm.acompletion` to verify routing,
prompt assembly, guardrail enforcement, and response shaping — the same technique used for
`MockEmbedding` in Sprint 3B. To test against a real provider, set `GROQ_API_KEY` (or any
other provider's key) in `.env` and the exact same code path runs for real, no changes
needed.

## Authentication & Authorization (Sprint 6)

Production-grade JWT auth, RBAC, and multi-tenancy — verified end to end
against a live server and real Postgres, not just unit-tested in isolation.

```
app/
├── models/
│   ├── organization.py     # the tenant boundary
│   ├── role.py              # 5 roles, seeded via migration (not hardcoded enum)
│   ├── user.py               # scoped to one Organization + one Role
│   └── refresh_token.py      # stores only a SHA-256 hash, never the raw token
├── security/                 # new top-level package
│   ├── password.py           # bcrypt hash/verify
│   ├── jwt.py                 # access/refresh token create + decode, type-checked
│   └── dependencies.py       # get_current_user, get_current_active_user, require_role()
├── repositories/
│   ├── user_repository.py
│   ├── organization_repository.py  # + RoleRepository, combined (both simple lookups)
│   └── refresh_token_repository.py # hash lookup, validity check, revoke
├── services/
│   └── auth_service.py       # register / login / refresh (rotation) / logout
├── schemas/auth.py
└── api/v1/
    ├── auth.py                # POST register, login, refresh, logout
    ├── users.py                # GET /users/me
    ├── organizations.py        # GET /organizations (scoped by role)
    └── roles.py                 # GET /roles
```

**Minimally touched, not regenerated**: `Copilot`/`KnowledgeSource` gained
one nullable `organization_id` column each (schema-ready for tenant
scoping); `ChatRequest.user_id` became optional (client no longer needs
to send it); `api/v1/chat.py` now requires authentication and overwrites
`payload.user_id` with the authenticated identity before it ever reaches
`ChatOrchestratorService` — **zero changes** to the orchestrator, the
LangGraph workflow, or any agent node. `core/dependencies.py` and
`api/router.py` gained new providers/mounts, additively.

### A deliberate scope decision

**The existing Copilot/KnowledgeSource/Document CRUD endpoints
(`/copilots`, `/knowledge-sources`, `/documents`) were *not* retrofitted
with mandatory authentication or tenant-scoped filtering in this sprint.**
Doing so would have meant rewriting several already-tested Sprint 2 files
and their full test suites — directly at odds with this sprint's own
"minimize modified files" and "preserve all existing functionality"
constraints, and a much larger, higher-risk change than the sprint's
primary ask. What *is* in place: the `organization_id` columns exist and
are ready, and chat — the one place explicitly required to change
authentication behavior — is fully protected and tenant-aware via the
authenticated user's `organization_id`. Recommend a follow-up sprint to
wire `Depends(CurrentUser)` + org-scoped filtering into those three
routers once this tradeoff is confirmed acceptable.

### Two real bugs found while building this (not just written and assumed correct)

1. **Role-seeding gap in tests**: the Sprint 6 migration seeds the 5 roles
   via a data-insertion step (`op.bulk_insert`) — but the test suite builds
   its schema via `Base.metadata.create_all()` for speed, which only
   creates tables, never runs migration-embedded data. Registration failed
   with `AttributeError: 'NoneType' object has no attribute 'id'` in every
   test until roles were seeded directly in `conftest.py`'s
   `setup_database` fixture too.
2. **`BaseRepository.list_all()`'s `created_at` assumption broke on `Role`**:
   the base repository (Sprint 2) orders every list query by
   `created_at.desc()`, documented as relying on "all current models expose
   `created_at`" — which stopped being true the moment a genuinely
   timestamp-free reference table (`Role`) was added. Fixed with a minimal
   override in `RoleRepository.list_all()`.
3. **An empty `.env.example` value is worse than an absent one**: initially
   wrote `JWT_SECRET_KEY=` (empty) in `.env.example`. Verified directly that
   pydantic-settings treats a present-but-empty env var as `""`, silently
   overriding the safe code-level dev default — the opposite of what an
   `.env.example` placeholder should do. Fixed by commenting the line out
   instead.

### Registration / role assignment rule

`POST /auth/register` takes an `organization_name`. If an organization
with that name already exists, the new user joins it as `end_user`; if
not, one is created and the registering user becomes its
`organization_admin`. Simple, self-service, no separate invite flow (out
of scope for this sprint).

### How to Test

**Via the frontend (Sprint 9 and later)**: the frontend now has a real
Sign Up page at `/register` that calls this exact endpoint — the
Swagger walkthrough below remains accurate and useful for testing the
backend in isolation, but end users (and most manual testing) should
go through the UI, not Swagger directly. The frontend supplies a
private, auto-generated `organization_name` per user (never derived
from email domain, never exposed as a visible field) — see the
frontend's `lib/workspace-name.ts` and its README for the exact scheme.

**1. Docker + migration:**
```bash
cd backend
docker compose up --build
docker compose exec api alembic upgrade head    # seeds the 5 roles
```

**2. Swagger sequence** at `http://localhost:8000/docs`:
1. `POST /api/v1/auth/register` — `{"email": "admin@acme.com", "password": "SecurePass123", "organization_name": "Acme Corp"}`
2. Click the **Authorize** button (top right) — enter the same email as
   username and your password. This POSTs to `/api/v1/auth/login` under
   the hood (OAuth2PasswordRequestForm, exactly what makes Swagger's
   Bearer auth work natively) and Swagger stores the access token for
   every subsequent request.
3. `GET /api/v1/users/me` — confirms you're authenticated as `organization_admin`.
4. `GET /api/v1/roles` — lists all 5 seeded roles.
5. `POST /api/v1/chat` — no `user_id` field needed; try it with a real
   `copilot_id` from the existing Copilot Management endpoints. Try it
   again with **no** Authorization header — confirms `401`.
6. `POST /api/v1/auth/refresh` with the refresh token from step 1's login
   response — confirms token rotation.
7. `POST /api/v1/auth/logout` with that same (now-rotated, current)
   refresh token, then try `/auth/refresh` again with it — confirms `401`
   (revoked).

**Sample register request/response:**
```json
POST /api/v1/auth/register
{ "email": "admin@acme.com", "password": "SecurePass123", "organization_name": "Acme Corp" }
```
```json
{
  "id": "4bc322b6-46d0-4118-8987-35d6c8aea8a8",
  "email": "admin@acme.com",
  "full_name": null,
  "is_active": true,
  "organization_id": "fb8ca471-1d44-498c-829e-a15b7beeb56e",
  "role": { "id": "37c835b4-...", "name": "organization_admin", "description": "Full access within their own organization." },
  "created_at": "2026-08-05T15:45:55.334376Z"
}
```

**3. Automated tests:**
```bash
cd backend
pip install -r requirements.txt
pytest tests/test_auth.py tests/test_chat.py -v
```
`test_auth.py` (15 tests) covers registration/role-assignment, login,
protected-endpoint 401s, refresh rotation + replay rejection, logout +
revocation. `test_chat.py` was updated (not regenerated) to add auth
headers to every existing call, plus 3 new tests: unauthenticated chat
→ 401, unauthenticated stream → 401, and — the key guarantee — that a
client-supplied `user_id` in the payload is silently ignored in favor of
the authenticated identity.

Every scenario above was also run manually against a live `uvicorn`
server and real Postgres before being formalized into tests — including
confirming a rotated refresh token becomes genuinely unusable and a
logged-out token can't be replayed.

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

## New Dependencies

**Sprint 3A:**

| Package | Why |
|---|---|
| `python-multipart` | Required by FastAPI/Starlette to parse `multipart/form-data` (file uploads) |
| `pymupdf` (imports as `fitz`) | PDF text extraction and page counting |
| `aiofiles` | Async file writes/reads in the storage service, off the event loop |

**Sprint 4:** none. Everything (provider interfaces, planner, guardrails,
prompt engine, correlation middleware) is built on Pydantic, FastAPI, and
the standard library (`abc`, `contextvars`, `enum`) already in the project.

**Sprint 3B:**

| Package | Why |
|---|---|
| `llama-index-core` | Hierarchical chunking, indexing, retrieval orchestration |
| `llama-index-embeddings-huggingface` | `BAAI/bge-small-en-v1.5` embeddings |
| `llama-index-vector-stores-qdrant` | Qdrant integration for LlamaIndex |
| `llama-index-retrievers-bm25` | BM25 sparse retrieval |
| `qdrant-client` | Vector database client (pinned to 1.18.0 — see version note in `requirements.txt`) |

**Sprint 5:**

| Package | Why |
|---|---|
| `langgraph` | Orchestration engine for the 5-node chat workflow |
| `litellm` | Unified call interface across OpenAI/Azure OpenAI/Anthropic/Groq/Ollama |

Also bumped in Sprint 5 (necessary, not optional — see `requirements.txt` comments):
`transformers` 4.44.2→4.48.3 and `tokenizers` 0.19.1→0.21.4, because `litellm` requires
`tokenizers>=0.21.0`, which the Sprint 3B pin couldn't satisfy. Re-verified the torch/numpy
ABI fix from Sprint 3B still holds with the new versions before shipping (full 65-test
regression suite, clean, before any Sprint 5 code was written).

**Sprint 6:**

| Package | Why |
|---|---|
| `pyjwt` | JWT access/refresh token creation and verification |
| `bcrypt` | Password hashing (used directly, not via passlib) |
| `email-validator` | Backs Pydantic's `EmailStr`, used for `UserRegister.email` |

## What's Intentionally Not Here

Per Sprint 5's explicit scope: the Sprint 3B retrieval implementation was not replaced (only
extended with query rewriting/re-ranking/confidence scoring as additive post-processing
steps). No real LLM provider was called end-to-end in this environment (no API key
available) — every integration test monkeypatches `litellm.acompletion`; see the Enterprise
AI Runtime section above for what that does and doesn't prove.

Per Sprint 6's explicit scope: the existing Copilot/KnowledgeSource/Document CRUD endpoints
were not retrofitted with mandatory authentication or tenant-scoped filtering — see "A
deliberate scope decision" under Authentication & Authorization above. No invite-based
registration flow (self-service org-join-by-name only). No password reset flow. No
super_admin bootstrap tooling (a super_admin user must currently be promoted directly in the
database — `UPDATE users SET role_id = (SELECT id FROM roles WHERE name = 'super_admin')
WHERE email = '...'`).
