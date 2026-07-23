# Task 3 Report: Implement the visible health journey

## Status

Done.

## Changes

- Completed the Vite/React entrypoint wiring in `apps/web/src/main.tsx` using the committed app shell.
- Replaced the placeholder app in `apps/web/src/App.tsx` with the visible health journey:
  - calls `fetchHealth()`
  - shows `Checking demo environment` while loading
  - shows `Demo environment healthy` on success
  - shows `Demo environment unavailable` on failure
- Added the approved public seam test in `apps/web/src/App.test.tsx` for both healthy and unavailable states.
- Added frontend test setup in `apps/web/src/test/setup.ts` and registered it from `apps/web/vite.config.ts`.
- Kept the page copy in English and stayed within scope: no Docker, database, authentication, routing, or React Query usage.

## Commands and results

1. `pnpm --filter web test -- App.test.tsx`
   - Result: failed before functional verification because `pnpm` attempted an interactive modules purge in a non-TTY environment.

2. `CI=true pnpm --filter web test -- App.test.tsx`
   - RED 1: failed because `test` was not imported in `src/App.test.tsx`.

3. `CI=true pnpm --filter web test -- App.test.tsx`
   - RED 2: failed because `App` was not exported/implemented as the required default component.

4. `CI=true pnpm --filter web test -- App.test.tsx`
   - Intermediate failure: `expect` was not imported in the test file.

5. `CI=true pnpm --filter web test -- App.test.tsx`
   - Intermediate failure: the second test observed two `role="status"` elements because cleanup was missing between tests.

6. `CI=true pnpm --filter web test -- App.test.tsx`
   - GREEN: passed.

7. `CI=true pnpm --filter web check`
   - GREEN: passed lint, build/typecheck, and all web tests.

## RED/GREEN evidence

### RED

- The focused `App` test initially failed before implementation because the placeholder app did not satisfy the visible health journey seam.
- The first functional failure after fixing the harness was:
  - `Element type is invalid... You likely forgot to export your component...`
- This confirmed the seam was not implemented yet.

### GREEN

- Focused run:
  - `src/App.test.tsx (2 tests)`: passed
- Full applicable web checks:
  - `pnpm --filter web check`: passed
  - Includes lint, build/typecheck, `src/api/health.test.ts`, and `src/App.test.tsx`

## Files changed

- `apps/web/index.html`
- `apps/web/src/App.tsx`
- `apps/web/src/App.test.tsx`
- `apps/web/src/main.tsx`
- `apps/web/src/test/setup.ts`
- `apps/web/src/vite-env.d.ts`
- `apps/web/vite.config.ts`
- `.superpowers/sdd/task-3-report.md`

## Self-review

- The UI behavior matches the brief exactly at the public seam:
  - healthy => `Demo environment healthy`
  - unavailable => `Demo environment unavailable`
- The loading state is present but not asserted as public contract; it stays harmless and in English.
- The component depends only on the existing `fetchHealth()` wrapper and does not introduce extra client state libraries or routing.
- Test coverage is behavior-first and mocks only the approved frontend seam.
- No unrelated repo files were modified for this task.

## Concerns

- `pnpm` required `CI=true` in this environment to avoid an interactive modules-directory prompt. With that set, all required checks passed.
