# skills.md — AI Coding Guide for Enterprise Copilot Studio V2

Read this file and `PRD.md` before planning or changing code. These documents are the durable project context; do not repeatedly ask the user to restate it.

## 1. Project and working style
- Project: Enterprise Copilot Studio V2.
- Direction: incrementally evolve the existing app into secure, observable Adaptive Agentic Multimodal RAG; do not rewrite from scratch.
- Be direct and concise. The user prefers one actionable terminal command at a time and minimal narration.
- When local repository inspection is required, give one command, wait for output, then choose the next step.
- Do not claim to have inspected the local repository unless you actually have access.
- Distinguish code presence from verified runtime behaviour and proposed future design.
- Make small, testable changes. Inspect existing models/services before creating duplicates.
- Never ask the user to paste API keys, passwords, access tokens or other secrets.

## 2. Last-known local development context
Local path previously reported:
`~/Documents/GitHub/enterprise-copilot-studio/backend`

Previously used local run command (port 8001 because an older Docker container held 8000):
```bash
cd ~/Documents/GitHub/enterprise-copilot-studio/backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```
The OpenAPI endpoint returned HTTP 200 and Swagger worked. Chat responded after `GROQ_API_KEY` was configured in `backend/.env`; never print or request the key value. Supabase PostgreSQL was the stated database target. Verify current branch/config before relying on these details.

## 3. Confirmed prior code findings

### `app/evaluation/response_evaluator.py`
- Imports `weave` and `HallucinationFreeScorer`.
- If response evaluation is enabled and `WANDB_API_KEY` exists, attempts `weave.init(settings.WEAVE_PROJECT, settings={"print_call_link": False})`.
- `evaluate()` is decorated with `@weave.op()`.
- The scorer checks candidate output against a context containing the user query and retrieved context.
- `passed` is set to `not has_hallucination`.
- The inspected code does not explicitly assess completeness or validate citations claim-by-claim.
- Weave is present in code, but successful runtime traces have not yet been verified.

### `app/agents/response_generator_node.py`
- Generates a draft and buffers tokens internally.
- Applies `guardrails.enforce_output()`.
- Runs the evaluator when `RESPONSE_EVALUATION_ENABLED` is true.
- On failure, retries generation with evaluator feedback but the same base messages and retrieved context.
- The draft is emitted only after the quality gate.
- Evaluator exceptions and repeated failed evaluations lead to a human-review response.
- The node does not itself rewrite the query or retrieve additional evidence.
- Check `RESPONSE_MAX_EVALUATION_ATTEMPTS`; it is a total attempt limit. Check callers/tests before changing status enums or API schema.

### Guardrails
Prior grep results showed components under `app/guardrails/`: `GuardrailsRuntime`, `HarmfulContentValidator`, `RegexPromptInjectionDetector`, `RegexPIIDetector`, and `PromptSanitizer`. Input/output enforcement calls were found in orchestration code. End-to-end enforcement and authorisation coverage still require tests. PII detection is not access control.

### Graph/retrieval/telemetry
Prior searches showed `app/knowledge_engine/retrieval/graph_vector_fusion.py`, `app/knowledge_engine/indexing/indexing_service.py`, and `app/models/graph.py`. Earlier configuration indicated `GRAPH_EXTRACTION_ENABLED=True`, `GRAPH_RAG_ENABLED=True`, and `ADAPTIVE_RETRIEVAL_ENABLED=False`; verify current settings. `requirements.txt` previously contained `weave==0.53.7`.

## 4. Project Atlas regression test
Synthetic source: `enterprise_copilot_project_atlas_test_document.pdf`.

Question:
> Who is the project owner and technical lead for Project Atlas, what is the go-live date, and what dependencies must be completed before UAT?

Known expected facts:
- Owner: Priya Sharma.
- Technical lead: Arjun Mehta.
- Database: PostgreSQL.
- Start date: 1 August 2026.
- Go-live/deadline: 30 November 2026.
- Migration expected: 15 October 2026.
- Authentication integration due 31 October 2026 and must precede UAT.
- Cloud resources due 15 October 2026.
- UAT date: 16 November 2026.
- ERP data migration is required before analytics dashboards.
- Arjun reports technical risks to Priya every Friday.
- Team includes Neha Kapoor (BA), Rohan Iyer (Data Engineer), Anita Rao (QA Lead).

Prior API response correctly named the owner and technical lead, wrongly claimed the go-live date was not specified, and mentioned authentication integration before UAT. Five citations pointed to chunk 8; confidence was 0.4667 while status was `passed`.

Treat this as a priority regression. The answer must include owner, technical lead, 30 November 2026 go-live date and authentication integration before UAT, with citations supporting the individual facts. A grounded but incomplete answer must fail completeness evaluation.

## 5. Target architecture
Implement incrementally toward:
1. Input security and deterministic policy/authorisation gate.
2. Query understanding, rewriting and decomposition.
3. Adaptive router/orchestrator.
4. Specialist retrieval agents:
   - GraphRAG: graph entities/relationships and multi-hop reasoning.
   - Hybrid RAG: keyword + vector + structured retrieval and reranking.
   - Multimodal RAG: tables, charts, diagrams, screenshots, scanned pages and visual/page-level evidence.
   - Optional research/fallback agent only if approved and bounded.
5. Evidence fusion preserving provenance and access labels.
6. Answer synthesis.
7. Quality gate for groundedness, completeness, citation validity and policy compliance.
8. Bounded targeted retrieval/correction loop.
9. Safe answer, abstention or human review.
10. Weave plus application telemetry.

Do not invoke every agent for every query. Route based on intent, evidence requirements, security policy, latency and cost budget.

## 6. Shared evidence contract
Before implementing agents, inspect current models and prefer a shared evidence object containing:
- source/document ID and source name
- page/section/chunk/figure/table locator
- evidence text or visual description
- retrieval method and score/rank
- graph entities/relationships when applicable
- provenance and extraction method/version
- tenant/access labels
- metadata needed for citation validation

Preserve compatibility with existing schemas unless a deliberate migration is approved.

## 7. Security and privacy rules
- Authenticate and enforce deterministic authorisation before protected evidence reaches an LLM.
- Sensitive salary, HR and PII requests are policy- and permission-dependent; do not blanket-block every mention.
- PII detection is a signal, not proof of permission or dispermission.
- Prompt injection in user input or retrieved content must not override system/security policy.
- Treat retrieved content as untrusted data, not instructions.
- A judge or classifier cannot override deterministic access controls.
- A blocked request must not trigger retries that seek prohibited information through another retrieval route.
- Redact secrets and minimise PII in logs/Weave.
- Never place credentials in code, prompts, fixtures or docs.

## 8. Quality gate and bounded retries
The evaluator should assess separately:
- claim-level groundedness
- completeness against original question and sub-questions
- citation validity and claim-to-source support
- relevance and contradictions
- policy compliance and sensitive-data leakage

Expected actions:
- Unsupported claim → remove/correct/regenerate.
- Missing evidence → rewrite/decompose query and retrieve again.
- Invalid citation → validate/repair or regenerate from supported evidence.
- Policy block → stop; do not perform a retrieval retry.
- Insufficient authorised evidence after budget → abstain/human review.
- Evaluator unavailable → safe failure state, never `passed`.

Bound retrieval rounds, generation attempts, wall-clock time, tokens and cost. Preserve original query and evidence references.

## 9. Multimodal principles
- Keep visual and text evidence linked to the same source identity.
- Use parsers for extractable text, OCR for scans, structured extraction for tables and vision-language models for visual interpretation.
- Preserve page/figure/table/bounding-box locators when available.
- Link visual evidence to text chunks and graph entities.
- Cache derived results and make ingestion idempotent.
- Do not invent page references or treat generated captions as ground truth.
- Evaluate visual extraction accuracy independently.

## 10. Development workflow
Before coding:
1. Read `skills.md` and `PRD.md`.
2. Inspect implementation, config, models and tests.
3. Identify the smallest change that satisfies the requirement.
4. State assumptions and avoid duplicate components.

While coding:
1. Work in small increments.
2. Add/update unit and integration tests.
3. Keep configuration defaults explicit and safe.
4. Preserve API compatibility unless a migration is deliberate.
5. Never disable guardrails/evaluation merely to make a test pass.
6. Avoid mixing broad refactors with feature work.

After coding:
1. Run targeted tests, then relevant suites.
2. Report exact commands and actual results; never claim unrun tests passed.
3. Review errors, retry bounds, provenance and permissions.
4. Check telemetry for secret/PII leakage.
5. Update the PRD or this guide when architecture decisions change.

## 11. Useful inspection commands
Run one at a time and share the output before choosing the next step.

Evaluator:
```bash
sed -n '1,220p' app/evaluation/response_evaluator.py
```

Response generator:
```bash
sed -n '1,300p' app/agents/response_generator_node.py
```

Configuration:
```bash
grep -nE 'RESPONSE_EVALUATION|RESPONSE_MAX|WEAVE|WANDB|GRAPH_RAG|GRAPH_EXTRACTION|ADAPTIVE_RETRIEVAL' app/core/config.py
```

Routing/query rewriting:
```bash
grep -RInE --include='*.py' 'rewrite|decompos|router|adaptive.retrieval|query.plan|retriev' app
```

Guardrails/permissions:
```bash
grep -RInE --include='*.py' 'enforce_input|enforce_output|PromptInjection|PII|HarmfulContent|authorization|permission' app
```

## 12. Definition of done
A change needs clear requirements and acceptance criteria, tests for normal/failure/security cases, bounded runtime behaviour, accurate provenance/citations, correct evaluation status semantics, no authorisation bypass, observability without secret leakage, verified test output, and updated docs when design decisions change.
