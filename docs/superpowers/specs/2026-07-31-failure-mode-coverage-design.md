# Failure-mode coverage and the provider port

Date: 2026-07-31
Status: approved

## Problem

The suite covers what the product does when everything works. It does not cover what it
does when something breaks. Two gaps make that concrete:

1. `QueryTimeoutError` and the SQLite interrupt path are never exercised by a test. The
   timeout exists as metadata and the endpoint maps it to 504, but nothing proves it fires.
2. There is no provider. `answer_contextual_question(question, recommendation,
   provider_available: bool)` takes a boolean; failure is simulated by the caller, so no
   test describes a slow, refusing, or malformed model.

A local Ollama (`qwen3.5:9b` on `:11434`) is available, which makes a real provider — and
therefore real provider failures — testable without a paid API.

## Design

### Provider port

```
answer_contextual_question(question, recommendation, provider)
                                    |
                    Protocol: complete(prompt, timeout) -> str
                    |               |                   |
        DeterministicProvider  OllamaProvider     test doubles
        (default, no network)  (opt-in by env)   (timeout / refuse / garbage)
```

- The default stays deterministic, so the public demo never depends on a local model.
- `OllamaProvider` is selected by `ADVISOR_PROVIDER=ollama` plus `OLLAMA_MODEL`.
- `explanations.py` stays pure: it derives text from the recommendation, no model.

**Model output is never trusted.** Whatever a provider returns passes through the existing
grounding checks — a citation is required, and customer-facing text goes through the SMS
clause allowlist. With a real model those nets stop being theoretical: if the model invents
a price, a test must show the system refuses it.

### Failure inventory

| Boundary | Scenario | Required behaviour |
| --- | --- | --- |
| SQL | query exceeds the 2s budget | `QueryTimeoutError` → 504 |
| SQL | handler aborts mid-query | `_shop_id` is cleared; the next request cannot inherit the tenant |
| SQL | a forged write reaches a `query_only` connection | refused as unsafe, not a 500 |
| Partial write | approval succeeds, reservation fails | an approved quote without an appointment must not become reservable once invalidated |
| Partial write | reservation succeeds, message fails | the appointment stands and the message can be retried |
| Partial write | check-in saved, recommendation raises | retry is consistent |
| Provider | slower than the timeout | degrade to the deterministic recommendation with its citation |
| Provider | connection refused | same degradation, never a 500 |
| Provider | truncated or malformed output | same, and no uncited text is delivered |
| Provider | invents a price | refused by validation, not by the model |
| Web | fetch fails on quote/approval/message | the Advisor sees a message, not an unhandled rejection |
| Web | API answers 500 | "unavailable" reads differently from "refused by a rule" |

### Test layers

- **Fast, hermetic** (majority): port doubles. A timing-out provider raises rather than
  sleeping. Always run.
- **Against real Ollama**: marked `@pytest.mark.ollama`, skipped when `:11434` does not
  answer. Proves the HTTP adapter and a real timeout. Never blocks `make check` or CI.
- **Live evaluation**: `make eval-live` runs the 100 canonical cases against the local
  model, grading each answer deterministically against the case's expected outcome. That
  deterministic grading is the ground truth the live-model gate was missing.

## Out of scope

- Replacing the deterministic path in the public demo. Cloud Run has no Ollama; wiring a
  hosted free API is a separate change.
- Retry policy tuning. One bounded retry then degrade, as today.

## Follow-on

Split `main.py` into per-feature routers, after this lands. Moving 1,700 lines is safer
once failure behaviour is pinned by tests.
