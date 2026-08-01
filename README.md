# Service Advisor AI

An AI service-advisor copilot for independent automotive shops. A Service Advisor checks a
vehicle in, receives a maintenance recommendation grounded in a reviewed manual with a
page-level citation, drafts a quote priced against shop inventory and bay capacity, approves
it through a command boundary, reserves an appointment and sends a simulated message.

The demo targets a single shop in Mexico while keeping the data model ready for
multi-tenancy.

## Live

- Web: deployed on Vercel
- API: <https://service-advisor-api-gemp.onrender.com> — try [`/docs`](https://service-advisor-api-gemp.onrender.com/docs),
  [`/health`](https://service-advisor-api-gemp.onrender.com/health) or
  [`/readiness`](https://service-advisor-api-gemp.onrender.com/readiness)

Both scale to zero, so the first request after an idle period wakes the service; the web
application reports that rather than failing.

## What it refuses to do

The interesting behaviour is the refusals, and each one is covered by tests:

- A recommendation with no reviewed rule for the exact model, engine, drivetrain and market
  says so instead of borrowing a neighbouring schedule.
- A rule whose manual publishes no distance — Honda's Maintenance Minder — answers that the
  odometer does not decide, rather than inventing a kilometre figure.
- A quote above MXN 15,000, a repeated decline, changed operational inputs or an unavailable
  part escalates to a Manager. Insufficient evidence is overridable by nobody.
- An approval is revalidated against live pricing, inventory and slots, expires after 24
  hours, and saves at most one quote.
- A customer message may only carry the approved facts plus whole approved clauses, so an
  invented price, service, recipient or urgency cannot reach the customer.
- Ad hoc questions run one parsed, read-only SELECT over tenant-filtered semantic views;
  quoted identifiers, comma joins, derived tables and system catalogs are all refused.
- Traces carry an allowlisted set of attributes, redacted at the source, so names, contact
  details and raw transcripts never reach observability.

## Known limitation: the maintenance sources

No public Mexican maintenance schedule binds model, year, engine and drivetrain for any of
the ten canonical vehicles. Every rule therefore cites the manufacturer's United States
manual, is labeled a fallback, and each recommendation names the market its evidence came
from. The fleet itself is synthetic and not a plausible Mexican line-up.

The research, its sources and the remaining limitations are in
[the source study](docs/research/2026-07-31-mexican-maintenance-sources.md).

## Documentation

- [MVP specification](docs/specs/service-advisor-ai-mvp.md)
- [Public demo deployment](docs/deployment/public-demo.md)

## Development

Install dependencies with `pnpm install` and `uv --directory apps/api sync --all-groups`.

- `make dev` starts the web application and API together.
- `make generate-api` regenerates the TypeScript client while the API is running.
- `make check` runs lint, static types and unit tests for both applications.
- `make check-ollama` runs the tests that need a local model, and is skipped without one.
- `make smoke` runs the browser health journey.

The language provider is deterministic by default, so the demo never depends on a model. Set
`ADVISOR_PROVIDER=ollama` to answer through a local one; whatever it returns is still held to
the same grounding rules.
