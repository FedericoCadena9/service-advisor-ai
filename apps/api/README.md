# Service Advisor AI — API

The API behind the Service Advisor demo: reviewed maintenance rules with page-level
citations, deterministic quote drafting against shop inventory and bay capacity,
human-approved quote commands, safe read-only SQL over tenant-filtered semantic views, and
simulated appointments and SMS.

Source and frontend: https://github.com/FedericoCadena9/service-advisor-ai

## Try it

- `GET /health` — liveness
- `GET /readiness` — release gates and the running versions; reports `cold_start` on the
  first request after the Space wakes
- `GET /release` — release, model, prompt, rule and dataset versions
- `GET /docs` — the full OpenAPI surface

Everything else needs a demo session:

```
curl -X POST <space-url>/demo-sessions -H 'Content-Type: application/json' -d '{"role":"advisor"}'
```

## Configuration

| Variable | Purpose |
| --- | --- |
| `ALLOWED_ORIGINS` | Comma-separated browser origins allowed to call the API. A wildcard is refused. |
| `DEMO_SESSION_SECRET` | Signs demo session tokens. |
| `ADVISOR_PROVIDER` | `deterministic` (default) or `ollama`. |
| `SMOKE_CHECK_PASSED`, `LIVE_MODEL_PROMOTION_APPROVED` | Release gate outcomes, read from the environment and never from a caller. |

## Data

All data is synthetic. The vehicles, customers, inventory and service history are seeded
demo records, and appointments and SMS are simulated: nothing is sent to a real phone.
