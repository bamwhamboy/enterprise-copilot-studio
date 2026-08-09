<div align="center">

# Enterprise Copilot Studio

**An enterprise-grade platform for composing, deploying, and chatting with AI copilots grounded in your own organization's documents.**

Hybrid retrieval-augmented generation · LangGraph orchestration · Multi-tenant JWT auth · Streaming chat with citations

[![Next.js](https://img.shields.io/badge/Next.js-15-black)](frontend/README.md)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688)](backend/README.md)
[![LangGraph](https://img.shields.io/badge/LangGraph-orchestration-1C3C3C)](backend/README.md#architecture)
[![Qdrant](https://img.shields.io/badge/Qdrant-vector%20search-DC244C)](backend/README.md#tech-stack)
[![License](https://img.shields.io/badge/license-unspecified-lightgrey)](#license)

[Live Demo](#) · [Backend Setup](backend/README.md) · [Frontend Setup](frontend/README.md) · [Architecture](#architecture)

</div>

---

## Live Demo

> **[your-app.vercel.app](#)** _— replace with the deployed Vercel URL._
>
> No demo account or seeded credentials are required — registration is
> self-service, and every new account gets its own private workspace
> automatically. See [Getting Started](#getting-started) below to spin up
> the full stack yourself instead.

## Demo Video

> _Drop the video in here — on GitHub, the easiest way is to open this
> file in the web editor and drag the video file directly into the
> text area; GitHub uploads it and inserts a working embed link
> automatically. A short GIF of the chat-with-citations moment above
> the video is a nice touch too, but not required._

## Overview

Most companies have mountains of internal documents — HR policies,
legal contracts, product manuals, onboarding guides — and no easy way
for employees to actually get answers from them. People either dig
through PDFs themselves or ping a coworker and wait.

Enterprise Copilot Studio solves that: it lets any organization turn
its own documents into a chatbot that actually knows the material.
Upload an HR policy, and employees can ask "how many sick days do I
get?" and get a real answer — with a citation pointing to the exact
document and section it came from, so nobody has to just trust the AI
blindly.

Each company that signs up gets its own private, isolated space —
nobody can see another organization's copilots, documents, or
conversations. Registration is instant and self-service: sign up, and
you're building your own AI assistant in minutes, no admin setup
required.

Under the hood, it's a full-stack platform for building
retrieval-grounded AI assistants without writing RAG infrastructure
from scratch: hierarchical document chunking, hybrid dense + sparse
retrieval, guardrails and PII masking, JWT authentication with
refresh-token rotation, and multi-tenant data isolation, all running on
real, memory-constrained infrastructure rather than a local-only demo.

## What Makes It Stand Out

**It doesn't make things up — it shows its work.** Every answer comes
with a confidence score and a citation back to the exact source
document. If the copilot doesn't know something, it says so, instead
of guessing.

**It's a real, working product — not a demo that only runs on one
laptop.** It's live on the internet right now, with a real database, a
real vector search engine, and real AI providers behind it. Anyone can
register and try it.

**Every company's data is genuinely private.** This wasn't an
afterthought — it's built in at every layer, so one organization's
documents, copilots, and chats are never visible to another, even by
accident.

**It survived real problems, not just a tutorial's happy path.**
Building this meant hitting genuine production issues — the app
running out of memory, a security gap that let one company briefly see
another's data — and actually fixing them, the same way a real
engineering team would. See [Engineering Highlights](#engineering-highlights)
below for the specifics.

**It's flexible by design.** It isn't locked into one AI provider — it
can run on Groq, OpenAI, Anthropic, or others, so it's never dependent
on a single company's model.

## Key Features

**Copilots**
- Guided 5-step creation wizard (type → knowledge sources → model →
  capabilities → review) with a live "Copilot Marketplace" template
  gallery
- Full CRUD management, each copilot independently configured and
  linked to one or more knowledge sources

**Knowledge & Retrieval**
- PDF upload with drag-and-drop, background text extraction, and
  hierarchical chunking (document → section → paragraph)
- Hybrid retrieval: dense vector search (Qdrant) fused with BM25 sparse
  search via reciprocal rank fusion, then re-ranked and confidence-scored
- Every chat response carries citations back to the exact source
  document and chunk

**Chat**
- Real-time streaming responses (Server-Sent Events) with a typing
  indicator, Markdown rendering, and per-message regenerate/copy actions
- Confidence scoring and expandable citation cards on every answer
- Conversation memory, isolated per user and per copilot

**Authentication & Multi-Tenancy**
- Self-service registration — no seeded demo accounts — each new user
  gets an automatically named, isolated workspace (never derived from
  email domain, to avoid grouping strangers who share a personal email
  provider into one organization)
- JWT access + refresh tokens with rotation and revocation, 5-role RBAC
  seeded at migration time

**Guardrails**
- Prompt-injection and jailbreak pattern detection on input
- PII detection and masking, harmful-content filtering on output

## Architecture

![Architecture diagram](docs/architecture-diagram.svg)

A chat turn flows: **input guardrails** → orchestrator resolves the
copilot and loads windowed conversation history → the **LangGraph
workflow** runs planner → hybrid retrieval (query rewrite, semantic +
BM25 fusion, re-rank, confidence score) → context assembly → the
**LiteLLM gateway** calls the configured provider → citations are
extracted → **output guardrails** mask PII and check for harmful
content → both turns are persisted.

The database, vector store, and API are deliberately three separate
managed services rather than one bundled deployment — see the backend
README's [Deployment](backend/README.md#deployment) section for setup
steps, and its [engineering log](backend/docs/ENGINEERING_LOG.md) for
the real production incident that shaped this decision.

## Tech Stack

| | |
|---|---|
| **Frontend** | Next.js 15 (App Router) · React 19 · TypeScript · Tailwind CSS v4 · shadcn/ui · Framer Motion · Zustand · TanStack Query |
| **Backend** | FastAPI · Python 3.12 · SQLAlchemy 2.0 (async) · Alembic · Pydantic v2 |
| **AI / RAG** | LangGraph · LiteLLM (Groq, OpenAI, Anthropic, Azure OpenAI, Ollama) · LlamaIndex · fastembed (ONNX Runtime) |
| **Data** | PostgreSQL · Qdrant (vector search) |
| **Auth** | JWT (PyJWT) · bcrypt · role-based access control |
| **Infra** | Docker · Vercel (frontend) · Railway (API) · Render (PostgreSQL) · Qdrant Cloud |
| **Testing** | pytest / pytest-asyncio (backend, 150 tests) · TypeScript strict mode + production build verification (frontend) |

## Repository Structure

```
enterprise-copilot-studio/
├── frontend/     Next.js application — see frontend/README.md
├── backend/      FastAPI application — see backend/README.md
└── docs/         Product requirements & architecture notes
```

Each subfolder is self-contained with its own dependencies, environment
configuration, and README. This root document is intentionally an
overview — detailed setup, environment variables, API documentation,
and deployment steps live in the two guides below.

## Getting Started

```bash
git clone https://github.com/bamwhamboy/enterprise-copilot-studio.git
cd enterprise-copilot-studio
```

Then follow, in order:

1. **[backend/README.md](backend/README.md)** — spin up PostgreSQL,
   Qdrant, and the API (Docker Compose is the fastest path; migrations
   run automatically).
2. **[frontend/README.md](frontend/README.md)** — install and run the
   Next.js app against that API.

Once both are running, registration is the only path in — there's no
demo account to look for.

## Engineering Highlights

A few things worth knowing about how this was actually built, beyond
the feature list:

- **A real production incident, root-caused and resolved.** Indexing
  began failing in production with no traceback — just the process
  getting killed. That investigation is documented start to finish in
  the backend's [engineering log](backend/docs/ENGINEERING_LOG.md):
  tracing it to PyTorch's own import overhead,
  replacing the embedding runtime with ONNX-based inference, discovering
  and fixing a *second*, unrelated cause (200MB of eagerly-imported chat
  dependencies loaded even for requests that never touched chat), and a
  *third* — an event-loop-blocking bug that could trigger a platform
  health-check kill independent of memory entirely. When the hosting
  tier's memory ceiling was still the limiting factor after three
  verified fixes, the conclusion was to migrate the API to a
  higher-memory platform rather than keep guessing in code — a real
  build-vs-buy tradeoff, not just a code problem.
- **A silent authentication bug in the vector database client.** An API
  key setting existed in config but was never actually passed to the
  Qdrant client — meaning it would appear to work while silently
  connecting unauthenticated. Found by tracing the actual client
  construction code, not assumed.
- **Multi-tenancy that avoids a real privacy pitfall.** New workspaces
  are never derived from a user's email domain — most people register
  with personal providers like Gmail, which would otherwise silently
  group unrelated strangers into the same organization.
- **Every fix in this repository is backed by a real test, not just
  reasoning about the code.** The backend's test suite runs against a
  real (in-memory) Qdrant and real PostgreSQL, not exclusively mocks —
  see the backend README's per-feature sections for what's verified
  where.

## Testing

```bash
# Backend
cd backend && pytest -v          # 150 tests

# Frontend
cd frontend && npm run build     # type-checked + production build
```

## Roadmap

A few items from the original product vision are intentionally not yet
built, and the UI says so rather than faking them: an AI cost/usage
dashboard, and native backend support for a handful of copilot
templates (Clinical Research, Customer Success, and a few others)
whose domain currently maps onto the closest existing category rather
than a dedicated one of its own — see the frontend's copilot template
catalog for exactly which.

## License

No license has been added to this repository yet — treat all rights as
reserved until one is. _(Consider adding a `LICENSE` file — MIT is a
common choice for a portfolio project like this.)_

## Author

Built by [**@bamwhamboy**](https://github.com/bamwhamboy).
