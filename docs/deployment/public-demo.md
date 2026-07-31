# Public scale-to-zero demo

The public demo runs the complete Advisor journey without a developer machine: the web
application is served from Vercel, the API runs on Cloud Run, and managed state lives in
InsForge. Everything scales to zero when the demo is idle.

## Setup

1. **Frontend (Vercel)** — import `apps/web` and let `apps/web/vercel.json` drive the build
   (`pnpm install --frozen-lockfile`, `pnpm build`, output `dist`). Set
   `VITE_API_BASE_URL` to the Cloud Run URL.
2. **API (Cloud Run)** — build the image and apply the service definition:
   ```
   gcloud run services replace deploy/cloud-run/service.yaml
   ```
   The definition pins the agreed settings: `minScale: 0` (scale to zero),
   `maxScale: 4`, `containerConcurrency: 40`, 512Mi memory, a 60 second request timeout,
   CPU throttling with startup boost, and a `/health` startup probe.
3. **Abuse controls** — the `abuseControls` block in the same file is applied through Cloud
   Armor: 60 requests per minute per IP, a burst of 20, a 64 KiB body cap, and a 300 second
   ban for offenders.
4. **InsForge** — apply `deploy/insforge/services.yaml`. Each service gets its own
   least-privilege credential: `demo_auth_client` for authentication, `advisor_app` for
   PostgreSQL writes, the read-only `semantic_reader` for pgvector and the semantic views,
   `voice_note_writer` for storage with a 24 hour retention, and
   `advisor_run_subscriber` for realtime.
5. **Secrets** — `DEMO_SESSION_SECRET` and `INSFORGE_DATABASE_URL` are mounted from Secret
   Manager; no secret is baked into the image or exposed to the browser.

## Release gates

`GET /readiness` runs the deterministic gates on every deploy and returns the recorded
versions:

| Gate | Type | Blocks deploy |
| --- | --- | --- |
| `migration` | automatic — backward-compatible steps only | yes |
| `health` | automatic — `GET /health` | yes |
| `smoke` | automatic — browser health journey (`make smoke`) | yes |
| `deterministic_evaluation` | automatic — canonical 100-case matrix thresholds | yes |
| `live_model_promotion` | **manual** — 100 cases replayed against the live model | no (blocks promotion) |

Migrations are additive only (`create_table`, `create_view`, `add_nullable_column`,
`add_index`), so the previous revision keeps serving during a rollout.

`GET /release` records the release, model, prompt, rule, and dataset versions for the
running revision.

## Provider limits

- Cloud Run: 4 instances, 40 concurrent requests each, 60 second timeout.
- Cloud Armor: 60 requests per minute per IP.
- Transcription: 90 seconds per voice note; failed audio is retained for 24 hours.
- Language model: one bounded retry per contextual answer, then a deterministic,
  citation-backed fallback.

## Recovery behavior

- **Cold start** — the first request after scale-to-zero reports `status: "waking"` with
  `cold_start: true`, and the web application shows that the demo is waking up while it
  retries.
- **Provider outage** — explanations and contextual chat degrade to the deterministic
  recommendation and its citation; transcription failures fall back to manual entry.
- **Failed gate** — `GET /readiness` returns 503 with the failing gate, and the previous
  revision keeps serving traffic.

## Manual live-model promotion gate

Promotion to live-model answers is never automatic. Replay the canonical 100 cases against
the live model, confirm the unsafe-SQL and prompt-injection blocking stay at 100 percent
and the overall score stays at or above 0.95, then call
`GET /readiness?live_model_promotion_approved=true` and record the reviewer with the
release manifest.
