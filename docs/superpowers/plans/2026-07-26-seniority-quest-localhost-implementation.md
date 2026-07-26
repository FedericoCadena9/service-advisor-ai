# Seniority Quest Localhost Implementation Plan

> **For Codex:** Execute this plan task by task with TDD. Keep the interview game isolated in `apps/interview-game`; do not replace the existing Service Advisor web application.

**Goal:** Deliver a local-first React interview-training game that helps Federico translate Vue experience into React language, rehearse senior-level technical answers and stories, and prepare for both the MedTrainer knowledge interview and a possible live challenge.

**Architecture:** A standalone Vite/React package owns a deterministic curriculum, a pure reducer for progression, a versioned local-storage adapter, and an accessible single-page mission UI. The browser provides missions, pressure controls, timers, notes, Story Forge, mastery, and persistence. Open-ended evaluation remains conversational: the UI produces a bilingual prompt that Federico answers in this Codex task, then records the resulting rubric scores locally.

**Tech Stack:** React 19, TypeScript, Vite, Vitest, Testing Library, Playwright, CSS.

---

## Public test seams

1. Rendered behavior: users can change language/mode, select an unlocked mission, prepare an answer prompt, record a rubric, and see mastery update.
2. Domain behavior: a pure reducer enforces unlock thresholds, boss gates, score calculation, and reset behavior.
3. Persistence behavior: a versioned adapter loads valid progress, rejects corrupt/obsolete data safely, and saves changes.
4. Browser journey: a fresh user completes one mission, persists progress across reload, and creates a story card.

## Task 1: Scaffold the isolated package

**Files:**

- Modify: `pnpm-workspace.yaml`
- Modify: `package.json`
- Create: `apps/interview-game/package.json`
- Create: `apps/interview-game/index.html`
- Create: `apps/interview-game/tsconfig.json`
- Create: `apps/interview-game/tsconfig.app.json`
- Create: `apps/interview-game/tsconfig.node.json`
- Create: `apps/interview-game/vite.config.ts`
- Create: `apps/interview-game/eslint.config.js`
- Create: `apps/interview-game/playwright.config.ts`
- Create: `apps/interview-game/src/main.tsx`
- Create: `apps/interview-game/src/test/setup.ts`
- Create: `apps/interview-game/src/vite-env.d.ts`

**Steps:**

1. Add `apps/interview-game` to the workspace and root scripts `interview:dev`, `interview:check`, and `interview:test:e2e`.
2. Declare React and the same compiler/test tooling versions already used by `apps/web`; add no runtime service or AI SDK.
3. Configure Vite/Vitest with jsdom and Playwright at `127.0.0.1:4174`.
4. Run `pnpm install` and `pnpm --filter interview-game exec tsc --noEmit` to verify the empty scaffold.

## Task 2: Build the progression domain test-first

**Files:**

- Create: `apps/interview-game/src/domain/game.test.ts`
- Create: `apps/interview-game/src/domain/game.ts`

**Behavior to specify:**

```ts
const initial = createInitialGameState()
const started = gameReducer(initial, { type: 'mission_started', missionId: 'bridge' })
const passed = gameReducer(started, {
  type: 'attempt_scored',
  missionId: 'bridge',
  scores: { clarity: 80, depth: 78, judgment: 82, evidence: 76, communication: 84 },
})

expect(passed.missions.bridge.status).toBe('passed')
expect(passed.missions.rendering.status).toBe('available')
```

1. Write failing tests for initial availability, weighted average, level pass at 75, boss pass at 80, critical-dimension floor at 65, retry behavior, and the 15-minute weakest-area allocation.
2. Run only `src/domain/game.test.ts` and confirm RED.
3. Implement typed mission metadata, rubric scoring, reducer actions, selectors, and immutable initial state.
4. Run the focused test and typecheck until GREEN.

## Task 3: Add local persistence test-first

**Files:**

- Create: `apps/interview-game/src/domain/storage.test.ts`
- Create: `apps/interview-game/src/domain/storage.ts`

**Behavior to specify:**

```ts
saveGameState(storage, state)
expect(loadGameState(storage)).toEqual(state)

storage.setItem(STORAGE_KEY, '{bad json')
expect(loadGameState(storage)).toEqual(createInitialGameState())
```

1. Write failing tests for save/load, corrupt JSON fallback, unsupported schema fallback, and reset.
2. Implement a `StorageLike` port and versioned payload (`schemaVersion: 1`) without reading browser globals in domain code.
3. Run the focused test, both domain test files, and typecheck.

## Task 4: Create the hard bilingual curriculum

**Files:**

- Create: `apps/interview-game/src/content/curriculum.test.ts`
- Create: `apps/interview-game/src/content/curriculum.ts`

**Curriculum contract:**

```ts
type Mission = {
  id: MissionId
  kind: 'level' | 'boss'
  minutes: number
  title: LocalizedText
  objective: LocalizedText
  vueBridge: LocalizedText
  prompts: Prompt[]
  framework: 'technical' | 'experience' | 'hypothetical'
}
```

1. Write validation tests requiring all seven missions, Spanish and English for every user-facing prompt, at least three prompts per mission, mixed prompt shapes, balanced correct-option positions, and no answer-length leakage above the agreed tolerance.
2. Confirm the curriculum test fails before content exists.
3. Add the journey: Vue→React bridge, rendering/state/effects, architecture/performance/testing, knowledge boss, Story Forge, challenge prologue, final simulation.
4. Include code forensics, ranking, competing plausible explanations, and open scenarios. Distractors must reflect real engineering trade-offs rather than obviously wrong syntax.
5. Run the curriculum tests and typecheck.

## Task 5: Build the mission-control UI test-first

**Files:**

- Create: `apps/interview-game/src/App.test.tsx`
- Create: `apps/interview-game/src/App.tsx`
- Create: `apps/interview-game/src/components/SkillMap.tsx`
- Create: `apps/interview-game/src/components/MissionBrief.tsx`
- Create: `apps/interview-game/src/components/RubricPanel.tsx`
- Create: `apps/interview-game/src/components/StoryForge.tsx`
- Create: `apps/interview-game/src/components/Countdown.tsx`
- Create: `apps/interview-game/src/hooks/useGame.ts`
- Create: `apps/interview-game/src/hooks/useCountdown.ts`

**Visible behavior to specify:**

1. Initial render identifies the interview, current mission, Vue→React bridge, and two modes.
2. Changing language immediately changes the mission copy; changing mode changes pressure guidance.
3. “Preparar respuesta” reveals a copyable prompt with the correct answer framework but never reveals a model answer.
4. A five-dimension rubric validates the critical floor, records the attempt, unlocks the next mission when appropriate, and updates mastery.
5. Story Forge captures Context, Problem, Decision, Rejected Alternative, Result, and Learning, then renders a reusable story card.
6. Reset requires explicit confirmation.

Run the single UI test file after each slice and typecheck after the reducer-connected slice.

## Task 6: Apply the tactical editorial visual system

**Files:**

- Create: `apps/interview-game/src/styles.css`
- Modify: `apps/interview-game/src/App.tsx`
- Modify: `apps/interview-game/src/components/*.tsx`

1. Establish deep graphite surfaces, amber mission accents, acid-green completion signals, restrained red warnings, sharp asymmetric panels, and mono/editorial type stacks.
2. Add a three-column desktop command layout and a clean single-column mobile layout.
3. Add purposeful entry/progress/timer motion and honor `prefers-reduced-motion`.
4. Ensure visible focus, meaningful landmarks, labelled controls, and minimum touch sizes.
5. Run the UI tests, lint, and build.

## Task 7: Prove the real browser journey

**Files:**

- Create: `apps/interview-game/tests/e2e/interview-journey.spec.ts`

**Journey:**

```ts
test('complete a mission and preserve progress @critical', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: /modo coach/i }).click()
  await page.getByRole('button', { name: /preparar respuesta/i }).click()
  await page.getByRole('button', { name: /evaluar intento/i }).click()
  // Fill five rubric sliders/inputs with passing evidence.
  await page.getByRole('button', { name: /registrar evaluación/i }).click()
  await expect(page.getByText(/misión superada/i)).toBeVisible()
  await page.reload()
  await expect(page.getByText(/misión superada/i)).toBeVisible()
})
```

1. Write the browser journey against accessible roles and labels; clear local storage in `beforeEach`.
2. Run the single E2E file with list reporter and repeat the critical test five times.
3. Fix only product or test behavior demonstrated by evidence; do not add arbitrary waits.

## Task 8: Verify, review, and commit

**Files:**

- Modify only files supported by verification or review evidence.

1. Run the focused domain tests, all unit/component tests once, lint, TypeScript build, and the E2E suite once from a fresh state.
2. Start the localhost server on port `4174` and inspect the real desktop and mobile UI.
3. Review changes against fixed point `dd89e9e` and the design spec `docs/superpowers/specs/2026-07-26-seniority-quest-interview-game-design.md` along Standards and Spec axes.
4. Resolve all High/Medium findings and re-run the affected focused checks plus the full verification command.
5. Stage only this plan, `apps/interview-game`, and intentional workspace manifest/lock changes. Do not stage `.superpowers/brainstorm`, unrelated research, or the pre-existing baseline plan.
6. Commit on the current branch with message `feat: add localhost seniority quest interview game`.
