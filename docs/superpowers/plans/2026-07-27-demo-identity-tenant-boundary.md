# Demo Identity and Tenant Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver issue #3 with signed, short-lived demo sessions and backend-enforced role, tenant, and overlay boundaries.

**Architecture:** The FastAPI API will sign compact HMAC tokens containing role, shop, demo-session, and expiry claims. A small SQLite-backed repository stores session overlays keyed by shop and demo-session; protected routes resolve and validate claims before reading or resetting only that overlay.

**Tech Stack:** Python 3.13, FastAPI, Pydantic, standard-library `sqlite3`, pytest/httpx, React TypeScript.

## Global Constraints

- Do not deploy or push.
- Tokens are short-lived and server-validated on every protected request.
- Roles are `advisor`, `manager`, and `admin`.
- Tenant and demo-session context must never be client-selectable after session creation.

---

### Task 1: Session domain and token codec

**Files:**
- Create: `apps/api/src/service_advisor_api/auth.py`
- Test: `apps/api/tests/test_auth.py`

**Interfaces:**
- Produces `create_demo_session(role: Role, now: datetime) -> str` and `verify_demo_session(token: str, now: datetime) -> SessionClaims`.

- [ ] **Step 1: Write the failing tests** for valid claims and expiration.
- [ ] **Step 2: Run** `uv --directory apps/api run pytest tests/test_auth.py -q` and confirm the missing module failure.
- [ ] **Step 3: Implement** HMAC signing, signature validation, fixed shop context, generated demo-session identifier, and expiration.
- [ ] **Step 4: Re-run** the focused test until it passes.

### Task 2: Protected overlay API

**Files:**
- Create: `apps/api/src/service_advisor_api/overlays.py`
- Modify: `apps/api/src/service_advisor_api/main.py`
- Test: `apps/api/tests/test_demo_sessions.py`

**Interfaces:**
- Produces `POST /demo-sessions`, `GET /workspace`, and `POST /workspace/reset`.
- `GET /workspace` permits Advisor, Manager, and Admin; the response is derived only from validated claims.

- [ ] **Step 1: Write failing API tests** for unauthenticated access, role denial, overlay isolation, and session-local reset.
- [ ] **Step 2: Run** `uv --directory apps/api run pytest tests/test_demo_sessions.py -q` and confirm failures caused by missing routes.
- [ ] **Step 3: Implement** the dependency that validates bearer tokens and the SQLite overlay store.
- [ ] **Step 4: Re-run** the focused tests until they pass.

### Task 3: Role-selection UI and contract regeneration

**Files:**
- Modify: `apps/web/src/App.tsx`
- Modify: `apps/web/src/App.test.tsx`
- Modify: `apps/web/src/api/*`
- Regenerate: `apps/web/src/api/generated/*`

- [ ] **Step 1: Write a failing component test** that chooses Advisor and observes protected workspace state.
- [ ] **Step 2: Run** `pnpm --filter web test -- App.test.tsx` and confirm it fails.
- [ ] **Step 3: Implement** a role selector that requests a backend session and uses its bearer token for workspace access.
- [ ] **Step 4: Regenerate** OpenAPI client while the API runs, then re-run the component test.

### Task 4: Verify and commit

- [ ] **Step 1: Run** `make check` and the focused browser/API tests.
- [ ] **Step 2: Review** `git diff --cached` for only #3 paths and no secrets.
- [ ] **Step 3: Commit** `fix(auth): establish signed demo sessions (#3)`.
