# Enterprise Copilot Studio - AI Project Context

## Project Overview

Enterprise Copilot Studio is an enterprise-grade AI platform that enables organizations to compose, deploy, and manage AI copilots using reusable AI components.

The MVP implements one fully functional HR Copilot while the architecture supports future copilots for Finance, Procurement, Sales, Legal, IT and Analytics.

This project is intended to demonstrate production-grade AI Engineering concepts rather than just a chatbot.

---

## Architecture Principles

- Modular
- Reusable
- Scalable
- Enterprise Ready
- API First
- AI First
- Cost Optimized
- Component Driven
- Low Coupling
- High Cohesion

---

## Technology Stack

Frontend
- Next.js 15
- React 19
- TypeScript
- TailwindCSS
- shadcn/ui
- Framer Motion
- React Query
- Zustand

Backend
- FastAPI
- SQLAlchemy
- PostgreSQL
- Redis

AI Stack
- LangGraph
- LlamaIndex
- LiteLLM
- Qdrant

Deployment
- Docker
- Docker Compose

---

## UI Philosophy

The application should look like a premium SaaS platform rather than a bootcamp project.

Design principles:

- Dark left sidebar
- Light workspace
- Rounded cards
- Soft shadows
- Glassmorphism where appropriate
- Purple/Blue accent colors
- Clean typography
- Minimalistic
- Enterprise feel

Inspired by:

- Vercel
- Linear
- Notion AI
- GitHub
- Azure AI Foundry

---

## AI Architecture

The platform should demonstrate:

- Enterprise Retrieval Engine
    - Hierarchical Hybrid RAG
    - Dense Vector Search
    - BM25 Keyword Search
    - Re-ranking
    - Context Compression
    - Context Summarization
    - Citation Generation

- Multi-Agent Orchestration (LangGraph)

- AI Middleware
    - Prompt Sanitization
    - Prompt Injection Detection
    - PII Detection
    - Guardrails
    - Semantic Cache
    - LLM Routing
    - Output Validation

- Memory Management
    - Conversation Memory
    - Context Management

- Tool Calling

- Cost Optimization

- Evaluation & Monitoring

---

## Coding Guidelines

- Reusable components only
- No duplicate code
- Strong typing
- Clean architecture
- Feature-based folder structure
- Enterprise coding standards

---

## MVP Scope

Only HR Copilot will be fully implemented.

Other copilots should appear as future templates.

The platform itself is the primary product.

HR Copilot is only the first implementation.

---

## Important

Whenever generating code, preserve the existing architecture and avoid introducing unnecessary complexity.
