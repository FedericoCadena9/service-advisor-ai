# Runnable Product Baseline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver issue #2: a locally runnable React and FastAPI baseline with a generated typed API client, health journey, automated checks, and CI.

**Architecture:** `apps/api` owns a dependency-free public health contract in FastAPI. `apps/web` calls that contract through code generated from the API's OpenAPI document and renders an accessible status. A root Makefile coordinates pnpm and uv commands without provisioning Docker or PostgreSQL.

**Tech Stack:** pnpm workspace, Vite, React, TypeScript, Vitest, Testing Library, Playwright, FastAPI, Pydantic, pytest, uv, Make, GitHub Actions, `@hey-api/openapi-ts`.

## Global Constraints

- Use English for code, schemas, test names, technical documentation, and UI copy.
- The frontend and API remain independently deployable from this monorepo.
- Docker Compose and PostgreSQL are out of scope until a persistence-dependent vertical slice.
- Tests assert public HTTP and visible UI behavior; they must not test private implementation details.
- `GET /health` must remain dependency-free and return a structured, typed response.
- Fast checks must include formatting, linting, static types, API tests, frontend tests, generated-client drift, and browser smoke coverage.

---

## File Structure

- `package.json`, `pnpm-workspace.yaml`, `Makefile`: workspace entry points and shared commands.
- `apps/api/pyproject.toml`, `apps/api/src/service_advisor_api/main.py`: Python package and FastAPI public application.
- `apps/api/tests/test_health.py`: public HTTP contract test.
- `apps/web/package.json`, `apps/web/vite.config.ts`, `apps/web/src/*`: Vite application and frontend checks.
- `apps/web/src/api/generated/*`: generated OpenAPI client output; never hand-edit.
- `apps/web/openapi-ts.config.ts`: API-client generator configuration.
- `apps/web/tests/e2e/health.spec.ts`: browser smoke journey.
- `.github/workflows/ci.yml`: repeatable pull-request and push validation.

### Task 1: Create the API health contract

**Files:**

- Create: `apps/api/pyproject.toml`
- Create: `apps/api/src/service_advisor_api/__init__.py`
- Create: `apps/api/src/service_advisor_api/main.py`
- Create: `apps/api/tests/test_health.py`

**Interfaces:**

- Produces: `GET /health` with HTTP 200 and JSON `{ "status": "healthy" }`.
- Produces: `service_advisor_api.main:app`, runnable by `uv run uvicorn service_advisor_api.main:app --port 8000`.

- [ ] **Step 1: Write the failing public HTTP test**

```python
from fastapi.testclient import TestClient

from service_advisor_api.main import app


def test_health_reports_a_healthy_demo_environment() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv --directory apps/api run pytest tests/test_health.py -q`

Expected: FAIL because `service_advisor_api.main` does not exist.

- [ ] **Step 3: Add the minimal API package and implementation**

```toml
# apps/api/pyproject.toml
[project]
name = "service-advisor-api"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = ["fastapi>=0.115", "uvicorn[standard]>=0.34"]

[dependency-groups]
dev = ["httpx>=0.28", "pytest>=8.3", "ruff>=0.9"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py313"
```

```python
# apps/api/src/service_advisor_api/main.py
from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["healthy"]


app = FastAPI(title="Service Advisor API", version="0.1.0")


@app.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    return HealthResponse(status="healthy")
```

- [ ] **Step 4: Run the API checks**

Run: `uv --directory apps/api run ruff check . && uv --directory apps/api run pytest tests/test_health.py -q`

Expected: ruff exits 0; pytest reports `1 passed`.

- [ ] **Step 5: Commit**

```bash
git add apps/api
git commit -m "feat(api): expose health contract"
```

### Task 2: Create the web workspace and generated API client

**Files:**

- Create: `package.json`
- Create: `pnpm-workspace.yaml`
- Create: `apps/web/package.json`
- Create: `apps/web/openapi-ts.config.ts`
- Create: `apps/web/src/api/generated/*`
- Create: `apps/web/src/api/health.ts`

**Interfaces:**

- Consumes: `http://127.0.0.1:8000/openapi.json`.
- Produces: `fetchHealth(): Promise<HealthResponse>` backed by generated client code.
- Produces: `pnpm generate:api`, which regenerates the client and produces no git diff when current.

- [ ] **Step 1: Create the workspace and generator configuration**

```json
// package.json
{
  "name": "service-advisor-ai",
  "private": true,
  "scripts": {
    "check": "pnpm --filter web check",
    "generate:api": "pnpm --filter web generate:api"
  },
  "devDependencies": { "concurrently": "^9.1.2" },
  "packageManager": "pnpm@11.6.0"
}
```

```yaml
# pnpm-workspace.yaml
packages:
  - apps/web
```

```json
// apps/web/package.json
{
  "name": "web",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "lint": "eslint .",
    "test": "vitest run",
    "test:e2e": "playwright test",
    "check": "pnpm lint && pnpm build && pnpm test",
    "generate:api": "openapi-ts"
  },
  "dependencies": { "@hey-api/client-fetch": "^0.10.0", "@tanstack/react-query": "^5.66.0", "react": "^19.0.0", "react-dom": "^19.0.0" },
  "devDependencies": { "@hey-api/openapi-ts": "^0.76.0", "@playwright/test": "^1.51.0", "@testing-library/jest-dom": "^6.6.0", "@testing-library/react": "^16.2.0", "@types/react": "^19.0.0", "@types/react-dom": "^19.0.0", "@vitejs/plugin-react": "^4.4.0", "eslint": "^9.20.0", "jsdom": "^26.0.0", "typescript": "^5.7.0", "vite": "^6.1.0", "vitest": "^3.0.0" }
}
```

```ts
// apps/web/openapi-ts.config.ts
import { defineConfig } from '@hey-api/openapi-ts'

export default defineConfig({
  input: process.env.OPENAPI_URL ?? 'http://127.0.0.1:8000/openapi.json',
  output: 'src/api/generated',
  plugins: ['@hey-api/client-fetch'],
})
```

- [ ] **Step 2: Start the API and generate the client**

Run: `uv --directory apps/api run uvicorn service_advisor_api.main:app --port 8000`

In another terminal run: `pnpm install && pnpm generate:api`

Expected: `apps/web/src/api/generated` contains the generated models and client files.

- [ ] **Step 3: Add the generated-client wrapper**

```ts
// apps/web/src/api/health.ts
import { client } from './generated/client'
import { getHealth } from './generated/sdk.gen'

client.setConfig({ baseUrl: import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000' })

export async function fetchHealth() {
  const { data, error } = await getHealth()
  if (error || !data) throw new Error('Health request failed')
  return data
}
```

- [ ] **Step 4: Verify generated-client drift is detectable**

Run: `pnpm generate:api && git diff --exit-code -- apps/web/src/api/generated`

Expected: exits 0.

- [ ] **Step 5: Commit**

```bash
git add package.json pnpm-workspace.yaml pnpm-lock.yaml apps/web
git commit -m "feat(web): add generated API client"
```

### Task 3: Implement the visible health journey

**Files:**

- Create: `apps/web/index.html`
- Create: `apps/web/src/main.tsx`
- Create: `apps/web/src/App.tsx`
- Create: `apps/web/src/App.test.tsx`
- Create: `apps/web/src/test/setup.ts`
- Create: `apps/web/tsconfig.json`
- Create: `apps/web/vite.config.ts`

**Interfaces:**

- Consumes: `fetchHealth(): Promise<{ status: "healthy" }>`.
- Produces: a page with `role="status"` stating either `Demo environment healthy` or `Demo environment unavailable`.

- [ ] **Step 1: Write the failing visible-behavior test**

```tsx
import { render, screen } from '@testing-library/react'
import { vi } from 'vitest'

import App from './App'

vi.mock('./api/health', () => ({
  fetchHealth: vi.fn().mockResolvedValue({ status: 'healthy' }),
}))

test('shows the healthy demo environment state', async () => {
  render(<App />)

  expect(await screen.findByRole('status')).toHaveTextContent('Demo environment healthy')
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pnpm --filter web test -- App.test.tsx`

Expected: FAIL because the React app does not exist.

- [ ] **Step 3: Implement the smallest visible journey**

```tsx
// apps/web/src/App.tsx
import { useEffect, useState } from 'react'

import { fetchHealth } from './api/health'

type HealthState = 'loading' | 'healthy' | 'unavailable'

export default function App() {
  const [state, setState] = useState<HealthState>('loading')

  useEffect(() => {
    fetchHealth().then(() => setState('healthy')).catch(() => setState('unavailable'))
  }, [])

  const message = state === 'healthy'
    ? 'Demo environment healthy'
    : state === 'unavailable'
      ? 'Demo environment unavailable'
      : 'Checking demo environment'

  return <main><h1>Service Advisor AI</h1><p role="status">{message}</p></main>
}
```

```tsx
// apps/web/src/main.tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import App from './App'

createRoot(document.getElementById('root')!).render(<StrictMode><App /></StrictMode>)
```

- [ ] **Step 4: Add the unavailable-state test and run frontend checks**

```tsx
vi.mocked(fetchHealth).mockRejectedValueOnce(new Error('offline'))
render(<App />)
expect(await screen.findByRole('status')).toHaveTextContent('Demo environment unavailable')
```

Run: `pnpm --filter web check`

Expected: lint, static typecheck, and both component tests pass.

- [ ] **Step 5: Commit**

```bash
git add apps/web
git commit -m "feat(web): show API health state"
```

### Task 4: Add shared commands, browser smoke test, and CI

**Files:**

- Create: `Makefile`
- Create: `apps/web/playwright.config.ts`
- Create: `apps/web/tests/e2e/health.spec.ts`
- Create: `.github/workflows/ci.yml`
- Modify: `README.md`

**Interfaces:**

- Produces: `make dev`, `make check`, `make smoke`, and `make generate-api`.
- Produces: a Playwright health journey that starts both services and observes the healthy UI.
- Produces: CI that runs the fast suite and verifies generated-client drift.

- [ ] **Step 1: Write the failing browser smoke test**

```ts
import { expect, test } from '@playwright/test'

test('loads the healthy demo environment', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('status')).toHaveText('Demo environment healthy')
})
```

- [ ] **Step 2: Run it to verify the missing configuration fails**

Run: `pnpm --filter web test:e2e`

Expected: FAIL because the Playwright web server configuration does not exist.

- [ ] **Step 3: Add command and test configuration**

```make
# Makefile
dev:
	pnpm exec concurrently --kill-others "uv --directory apps/api run uvicorn service_advisor_api.main:app --port 8000" "pnpm --filter web dev --host 127.0.0.1"

generate-api:
	pnpm generate:api

check:
	uv --directory apps/api run ruff check .
	uv --directory apps/api run pytest -q
	pnpm check

smoke:
	pnpm --filter web test:e2e
```

```ts
// apps/web/playwright.config.ts
import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  use: { baseURL: 'http://127.0.0.1:5173' },
  webServer: [
    { command: 'uv --directory ../api run uvicorn service_advisor_api.main:app --port 8000', port: 8000 },
    { command: 'pnpm dev --host 127.0.0.1', port: 5173 },
  ],
})
```

```yaml
# .github/workflows/ci.yml
name: CI
on: [pull_request, push]
jobs:
  fast-checks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 22, cache: pnpm }
      - uses: pnpm/action-setup@v4
        with: { version: 11.6.0 }
      - uses: astral-sh/setup-uv@v5
      - run: pnpm install --frozen-lockfile
      - run: uv --directory apps/api sync --all-groups
      - run: make generate-api
      - run: git diff --exit-code -- apps/web/src/api/generated
      - run: make check
      - run: pnpm --filter web exec playwright install --with-deps chromium
      - run: make smoke
```

- [ ] **Step 4: Run the full baseline suite**

Run: `make check && make smoke`

Expected: API tests, frontend checks, and browser smoke test pass.

- [ ] **Step 5: Document local workflow and commit**

Add `make dev`, `make check`, `make smoke`, and `make generate-api` to `README.md`.

```bash
git add Makefile README.md apps/web .github/workflows/ci.yml
git commit -m "ci: validate runnable product baseline"
```

## Plan Self-Review

- **Spec coverage:** Task 1 supplies the local API and public health contract. Tasks 2 and 3 supply the typed generated frontend client and visible health state. Task 4 supplies documented local startup, smoke coverage, fast checks, and CI. Docker and PostgreSQL are expressly deferred.
- **Placeholder scan:** The plan contains no deferred implementation markers or unspecified error-handling work.
- **Type consistency:** `HealthResponse` is generated from the FastAPI response model and is consumed through `fetchHealth`; the UI only relies on its `status` field.
