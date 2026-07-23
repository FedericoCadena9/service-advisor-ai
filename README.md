# Service Advisor AI

An AI service-advisor copilot for independent automotive shops. It combines reviewed maintenance rules, grounded document retrieval, read-only operational queries, voice transcription, and human-approved workflows to prepare auditable service recommendations and quotations.

The initial demo targets a single shop in Mexico while keeping the data model ready for multi-tenancy.

## Status

Product specification complete. Implementation has not started.

See [the MVP specification](docs/specs/service-advisor-ai-mvp.md).

## Development

Install dependencies with `pnpm install` and `uv --directory apps/api sync --all-groups`.

- `make dev` starts the web application and API together.
- `make generate-api` regenerates the TypeScript client while the API is running.
- `make check` runs format/lint checks, static types, and unit tests.
- `make smoke` runs the browser health journey.
