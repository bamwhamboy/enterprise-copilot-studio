# Product Requirements Document (PRD)
## Enterprise Copilot Studio V2 — Adaptive Agentic Multimodal RAG

**Status:** Working draft  
**Updated:** 16 October 2026

## 1. Executive summary
Evolve the existing Enterprise Copilot Studio V2 into a secure, observable Adaptive Agentic RAG platform. This is an incremental evolution, not a rewrite. A router/orchestrator should select the right retrieval path for each query and combine evidence where useful.

Target capabilities:
- GraphRAG for entities, relationships and multi-hop questions.
- Hybrid RAG combining keyword/BM25, vector retrieval, structured filters and reranking.
- Multimodal RAG for tables, charts, diagrams, screenshots, scanned pages and embedded figures.
- Query understanding, rewriting and decomposition.
- Specialist retrieval agents coordinated by a router.
- Guardrails, authentication, authorisation and privacy controls.
- Answer evaluation for groundedness, completeness and citations.
- Bounded retrieval/correction loops and safe abstention.
- Weights & Biases Weave plus application telemetry for observability.

## 2. Problem statement
A Project Atlas test asked for project owner, technical lead, go-live date and dependencies before UAT. The answer correctly named the owner and technical lead and mentioned authentication integration, but incorrectly claimed the go-live date was unavailable. All five citations pointed to the same chunk, yet the evaluation status was `passed`.

The inspected response generator retries generation against the same retrieved context; it does not itself request more evidence. A hallucination-only judge may accept a grounded but incomplete answer. The system must evaluate completeness and evidence coverage as well as groundedness.

## 3. Product goals
1. Improve retrieval recall and completeness for compound questions.
2. Select retrieval strategies and models dynamically.
3. Support text, graph, structured and visual evidence.
4. Trace material claims to authorised source evidence.
5. Enforce security and privacy throughout the request lifecycle.
6. Let evaluation outcomes trigger targeted retrieval or correction.
7. Keep model selection, retries, deadlines, token usage and cost configurable.
8. Instrument key decisions and failures.

Non-goals for initial phases: rewriting the whole backend, unbounded autonomous agents, calling every agent/model for every query, treating an LLM as the authority for access control, or enabling external web research by default.

## 4. Current-state baseline

### Present in inspected code (runtime still requires verification)
- FastAPI chat backend and LangGraph workflow.
- Graph extraction/GraphRAG-related components and graph-vector fusion code.
- Supabase PostgreSQL as the stated database target.
- Guardrail runtime, input/output enforcement, prompt-injection detection, PII detection and harmful-content validation.
- `ResponseEvaluator` using Weave's `HallucinationFreeScorer`.
- `@weave.op()` on evaluator; `weave.init()` attempted when `WANDB_API_KEY` is configured.
- Response generation retries after a failed evaluation; drafts are buffered until the quality gate.
- Repeated failure or evaluator exception leads to a human-review response.
- Configurable model gateway and `RESPONSE_EVALUATION_ENABLED` / `RESPONSE_MAX_EVALUATION_ATTEMPTS`.

### Must verify
- Weave traces actually appear in the intended project.
- The scorer SDK response contract matches code expectations.
- GraphRAG and guardrails run end-to-end in the deployed configuration.
- Citation metadata and claim-to-citation support are correct.
- Query rewriting/decomposition and multimodal ingestion capabilities already available elsewhere.
- Current config defaults and API status enum compatibility.

## 5. Target architecture

### Request control plane
1. Authenticate caller and establish tenant/organisation, identity and roles.
2. Apply deterministic policy checks; detect prompt injection, harmful requests and attempts to obtain secrets.
3. Identify sensitive-data requests (PII, salary, HR, financial and personal records).
4. Enforce authorisation using identity, document permissions, data classification and approved purpose. PII detection alone is not access control.
5. Understand intent, decompose compound questions and rewrite retrieval queries without changing intent.
6. Route to the appropriate specialist agent(s) within explicit budgets and deadlines.

### Specialist agents
- **GraphRAG agent:** graph entities/relationships, traversal and multi-hop reasoning.
- **Hybrid RAG agent:** keyword/BM25, vector search, structured filters and reranking.
- **Multimodal RAG agent:** evidence from tables, charts, diagrams, screenshots, scanned pages and embedded figures.
- **Optional fallback/research agent:** only if explicitly approved and bounded; external web research off by default.

All agents should return a common evidence structure: source/document ID, page/section/chunk/figure/table locator, evidence text or visual description, retrieval method, rank/score, provenance, extraction method/version and access labels. Avoid untraceable prose-only agent outputs.

### Evidence fusion and synthesis
- Deduplicate evidence while preserving provenance.
- Track which sub-questions are supported and which remain unanswered.
- Resolve conflicting sources explicitly.
- Associate material answer claims with supporting evidence.
- Preserve existing API contracts unless a deliberate, tested migration is approved.

### Quality gate
Evaluate separately:
- Claim-level groundedness / unsupported statements.
- Completeness against the original query and sub-questions.
- Citation validity and claim-to-source support.
- Contradictions, relevance and uncertainty.
- Policy compliance and sensitive-data leakage.

Statuses should distinguish `passed`, `corrected`, `human_review_required`, `disabled` (only when explicitly configured), and evaluator failure/unavailability or equivalent safe handling. Evaluator failure must never be recorded as success.

### Bounded adaptive loop
- Unsupported claims → correct/remove claims or regenerate.
- Missing evidence → rewrite/decompose query and retrieve again.
- Invalid citations → repair or regenerate from valid evidence.
- Policy block → never retry by seeking prohibited information through another path.
- Enforce maximum retrieval rounds, generation attempts, time, token and cost budgets.
- If authorised evidence remains insufficient, abstain or escalate for human review.

## 6. Query planning
Preserve the original question; identify entities, dates, metrics and constraints; split compound questions; generate useful retrieval variants without changing meaning; and record safe routing rationale. Minimise or redact sensitive values in traces. Use deterministic routing for clear/simple cases where practical.

## 7. Security and privacy
- Authenticate and authorise before protected evidence reaches an LLM.
- Enforce tenant, document and row-level permissions where applicable.
- Treat retrieved content as untrusted data, never as instructions that override system policy.
- Salary/HR/PII handling must be policy- and permission-based; do not blanket-block every mention of these topics.
- LLM classifiers and judges cannot override deterministic access controls.
- Blocked requests must not trigger unsafe retries.
- Redact credentials and minimise PII in logs and Weave traces.
- Log policy decisions without retaining unnecessary sensitive payloads.

## 8. Multimodal ingestion
Detect text, tables, figures, charts and scans. Reuse parsers for extractable text; use OCR for scanned pages, structured extraction for tables/numbers and vision-language models for visual interpretation. Preserve document/page/figure/table/bounding-box locators, link visual evidence to text and graph entities, cache derived outputs, make ingestion idempotent and observable, and expose extraction failures. Model-generated captions require provenance and evaluation.

## 9. Model strategy
Make router, graph reasoning, vision, embeddings/reranking, answer synthesis and judge model choices configurable by task. Use fallbacks only when configured. Record model IDs and usage metadata. Do not send every query through every model.

## 10. Observability and evaluation
Instrument correlation IDs; safe query classification/rewrites; router decision and selected agents; retrieval counts, scores and source IDs; sub-question evidence coverage; generation model, usage, latency and retries; judge outcomes; citation validation; guardrail decisions; and final status/abstention reason. Verify actual Weave traces; `@weave.op()` alone does not prove telemetry is working. Telemetry failure must not silently disable quality evaluation.

## 11. Acceptance criteria
### Retrieval
- Compound questions whose answers span multiple chunks return all supported facts.
- Project Atlas regression answer includes owner Priya Sharma, technical lead Arjun Mehta, go-live 30 November 2026 and authentication integration before UAT, with citations supporting individual facts.
- A grounded but incomplete answer fails completeness evaluation.
- Missing evidence triggers targeted retrieval or explicit uncertainty, not a false claim that the source lacks the fact.
- Distinct facts are not all cited to the same chunk when separate evidence is needed.

### Evaluation
- Unsupported claims fail groundedness checks.
- Invalid or irrelevant citations fail citation validation.
- Failed checks trigger the correct bounded action.
- Evaluator unavailability never produces `passed`.
- Unverified drafts are never streamed.

### Security
- Unauthorised sensitive-data requests are blocked before protected evidence reaches a model.
- Authorised access remains possible according to policy.
- Prompt injection cannot override policy.
- Blocked requests do not initiate unsafe retrieval retries.
- Sensitive payloads are minimised in telemetry.

### Multimodal and operations
- Test body text, tables, charts, diagrams and scanned pages.
- Visual facts retain source locators and can be cited.
- Extraction failures are visible and do not produce fabricated answers.
- Agents respect time, retry, token and cost budgets.
- Weave traces are verified in the configured project.
- API changes are compatible or deliberately versioned.

## 12. Suggested delivery phases
1. Baseline tests: config, evaluator contract, Weave traces, guardrails and Project Atlas regression.
2. Quality gate: completeness, citation validation, explicit evaluator failure and safe retry semantics.
3. Query planning and adaptive retrieval: rewrite/decomposition, shared evidence contract, router and bounded loop.
4. Hybrid/GraphRAG coordination and evidence fusion.
5. Multimodal ingestion/retrieval with provenance.
6. Security hardening, evaluation benchmarks, tracing, latency/cost optimisation and staged rollout.

## 13. Open questions
- Exact deployed graph/vector stores and configuration.
- Priority multimodal formats.
- Existing tenant/document-level permission metadata.
- Public API contract for evaluation status and citations.
- Latency and per-query cost targets.
- Approved model providers for enterprise data.
- Whether external web search is permitted.
- Human-review destination/ownership.
- Weave retention and redaction configuration.

## 14. Working principles
Inspect before changing; reuse existing components; implement small testable increments; do not equate config flags with runtime proof; preserve provenance and access labels; use deterministic permission controls; keep agent loops bounded and observable; a fluent answer is not necessarily complete or correct.
