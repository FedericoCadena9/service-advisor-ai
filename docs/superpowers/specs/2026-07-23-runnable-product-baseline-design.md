# Runnable Product Baseline Design

## Scope

Issue #2 establishes the smallest runnable foundation for the Service Advisor AI project. It provides a local React frontend and FastAPI backend, a typed OpenAPI-derived client, an observable health journey, fast automated checks, and continuous integration. It intentionally excludes Docker Compose, PostgreSQL, authentication, sessions, and domain workflows; PostgreSQL begins with the first slice that needs it.

## Structure

- `apps/web` is a Vite React TypeScript application managed with pnpm.
- `apps/api` is a FastAPI application managed with uv.
- The API exposes `GET /health`, which returns the public health contract and contributes to FastAPI's OpenAPI document.
- Generated TypeScript client code lives in the web application and is regenerated from the API contract through a documented command.
- A small Makefile provides the shared `dev`, `check`, and client-generation commands.

## User Journey

1. A developer runs `make dev`.
2. The web and API start locally without Docker or database services.
3. The web page calls the generated client.
4. The page clearly renders a healthy or unavailable demo-environment state.

## Failure Handling

If the health request fails, the interface displays an unavailable state instead of presenting stale or fabricated health data. The health endpoint remains dependency-free in this slice so it is reliable before persistence is introduced.

## Test Seams

- **API HTTP seam:** a FastAPI test verifies the public `GET /health` response contract.
- **Frontend visible-behavior seam:** a component test verifies the rendered healthy and unavailable states through the generated client boundary.
- **Browser smoke seam:** an end-to-end smoke test loads the application with the API available and observes the healthy state.

## Verification

Fast checks cover formatting, linting, static types, unit tests, and the browser smoke test. GitHub Actions runs the same checks for pull requests and pushes. The full suite is intentionally small at this baseline and is run once before the implementation is completed.

## Deferred Work

Docker Compose and PostgreSQL are deferred until the first persistence-dependent vertical slice. Authentication, tenant boundaries, demo sessions, and all Advisor domain behavior are separately scoped to later issues.
