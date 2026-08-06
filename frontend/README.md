# Enterprise Copilot Studio — Frontend

A Next.js 15 / React 19 frontend for Enterprise Copilot Studio: compose,
deploy, and chat with AI copilots grounded in your organization's own
documents (LangGraph orchestration, LiteLLM, hybrid RAG via Qdrant, all
served from the companion FastAPI backend).

## Getting Started

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The app expects a
running backend at `http://localhost:8000/api/v1` by default — set
`NEXT_PUBLIC_API_BASE_URL` in `.env.local` to point elsewhere.

## Authentication

**There is no demo account.** Every user creates their own account —
the app is not seeded with, and does not depend on, any hardcoded
credentials (no `vijay@example.com`, no `demo@example.com`, nothing
baked into the frontend). If your backend database happens to have
seeded users from earlier development/testing, they still work fine
via the Login page — the app just never *requires* one.

**Sign up** (`/register`): collects Full Name, Email, Password, and
Confirm Password. Every new account gets its own private workspace
(Organization) automatically — there's no visible "organization name"
field, and it's deliberately *not* derived from the user's email
domain (most people register with personal providers like Gmail or
Outlook, which would otherwise incorrectly group unrelated strangers
into the same organization). The registering user becomes that
workspace's admin. See `lib/workspace-name.ts` for the exact naming
scheme and why a uniqueness suffix is required, not cosmetic.

After a successful sign-up, the app logs the new user in immediately
and lands them on the Dashboard — no separate manual login step. If
that auto-login step ever fails for some transient reason (the account
itself was still created successfully), it falls back to the Login
page with a "Account created successfully. Please sign in." message
instead of showing an error.

**Sign in** (`/login`): standard email + password, with a working
"Remember me" (uses `sessionStorage` when unchecked, so the session
ends when the browser closes, vs. `localStorage` when checked).

Both pages share one branding panel and loading-state component
(`components/auth/`), so they stay visually identical by construction
rather than by manual upkeep.

## Project Structure

```
app/                  Next.js App Router pages
├── login/             Sign in
├── register/          Sign up (Sprint 9)
├── copilots/          Copilot management + chat workspace
├── knowledge-sources/ Knowledge source management + document upload
├── documents/         Cross-source document table
├── create-copilot/    Guided copilot creation wizard
├── marketplace/       Copilot template gallery
└── settings/          Profile, organization, and per-copilot model info
components/            UI primitives (components/ui) + feature components
lib/                   API clients, framework-agnostic helpers
store/                 Zustand stores (auth, chat sessions, sidebar, theme)
types/                 Shared TypeScript types, matching the backend's schemas
```

## Testing the Full Flow

```
Create Account  →  Dashboard  →  Create Copilot  →  Upload a document
      →  Launch Copilot  →  Ask a question  →  Logout  →  Login again
```

None of this requires any pre-existing account or seeded credentials —
registering a brand-new account is enough to exercise the entire
product end to end.

## Build

```bash
npm run build
```
