# Seniority Quest: Interview Game Design

Date: 2026-07-26

## 1. Context

Federico is interviewing for MedTrainer's Software Engineer Frontend - React role. The immediate stage is a 20–30 minute Technical Knowledge Interview; a 40–60 minute live Technical Challenge follows if he advances.

His recent production work has primarily used Vue 3, with both Options API and Composition API. He previously worked directly with React and now uses React in AI-assisted development workflows, with more emphasis on decomposition, delegation, validation, and technical outcomes than on manually writing every line. The preparation must recover React-specific semantics without discarding the senior frontend judgment developed through Vue.

The product is a difficult, game-like journey that runs inside this Codex task. Codex provides the adaptive interview intelligence, while a localhost interface displays missions, timers, progress, stories, scores, and unlocks.

## 2. Goal

Make seniority visible independently of framework syntax. By the interview, Federico should be able to:

1. Explain frontend concepts accurately in the React mental model.
2. Translate relevant Vue experience into credible React-oriented decisions.
3. Defend decisions through constraints, alternatives, trade-offs, evidence, testing, and measurement.
4. Tell concise, truthful stories that survive hostile follow-up questions.
5. Maintain technical precision when the interviewer changes between Spanish and English.
6. Read and modify a small React implementation without relying on AI for the first attempt.

## 3. Scope

### Primary scope

- Technical Knowledge Interview preparation.
- React, TypeScript, SPA architecture, state ownership, TanStack Query, Redux/Context, testing, debugging, performance, Design Systems, Git/SDLC, and AI-assisted engineering.
- Vue-to-React conceptual translation.
- Story extraction and technical cross-examination.
- Bilingual practice.

### Secondary scope

- A short Technical Challenge prologue that restores hands-on React reading and modification.
- Expansion into a deeper coding track only after the Technical Knowledge Interview.

### Non-goals

- Teaching frontend engineering from the beginning.
- Memorizing an exhaustive React API reference.
- Building a standalone cloud product, authentication system, remote database, or independent AI service.
- Predicting exact MedTrainer questions.
- Generating polished but unverified career stories.

## 4. Selected Approach

The selected format is **Skill Tree + Boss Fights**, with Story Forge and Interview Gauntlet mechanics embedded inside it.

- **Coach Mode** teaches, probes, gives bounded hints, and requires a transfer attempt after correction.
- **Interview Mode** gives no help, withholds feedback until the attempt closes, and uses adversarial follow-ups.
- Difficulty is progressive during levels and 9/10 during bosses.
- The first journey targets tomorrow's interview and leaves a bridge into live coding.

## 5. Journey

### Level 0: Calibration Gate

Purpose: establish the real starting point without assistance.

- React rendering and state snapshot diagnostic.
- Vue-to-React translation diagnostic.
- Available story inventory.
- Short English technical switch.
- Produces the initial Gap Log and may reallocate up to 15 minutes to the highest-risk gap.

### Level 1: Framework Translator

Purpose: replace approximate vocabulary with the React mental model.

- Function components and JSX versus Vue SFC/template execution.
- `ref`/`reactive` versus `useState`/`useReducer`.
- `computed` versus render-time derivation and optional `useMemo`.
- `watch`/`watchEffect` versus events, Effects, and server-state libraries.
- Props/emits versus props/callbacks.
- Composables versus custom Hooks.
- Slots versus `children` and render props.
- `provide`/`inject` versus Context.
- Pinia versus Redux Toolkit.
- Vue Query versus React Query.

### Level 2: State Strategist

Purpose: choose state ownership from requirements rather than library preference.

- Local UI state.
- Lifted shared state.
- Context for cross-cutting values.
- Redux for complex client-side workflows and event-driven state.
- TanStack Query for remote asynchronous state.
- Cache freshness, invalidation, optimistic updates, retries, and failure states.
- Effects, cleanup, cancellation, race conditions, and stale closures.

### Level 3: Architecture Guardian

Purpose: surface senior engineering judgment.

- SPA boundaries and feature organization.
- Reusable components and Design Systems.
- API integration and backend collaboration.
- Testing allocation across unit, component/integration, and Cypress E2E.
- Performance investigation before optimization.
- Production debugging, incident handling, and prevention.
- Code review, refactoring decisions, and delivery lifecycle.
- Responsible AI-assisted development and accountability.

### Level 4: Story Forge

Purpose: convert real experience into reusable, defensible stories.

- Four deep Story Cards.
- Two 30-second supporting examples.
- Spanish and English versions.
- React Bridge for each story.
- Cross-examination until the story survives ownership and evidence probes.

### Boss 1: Technical Knowledge Interview

Purpose: simulate the real stage.

- 20–30 minutes.
- Primarily Spanish, with unpredictable English follow-ups.
- No hints or mid-round feedback.
- Technical breadth, project depth, problem solving, and questions for the interviewer.
- Produces a score, red flags, and the top three corrections.

### Level 5: Technical Challenge Prologue

Purpose: prepare for the next stage without consuming the primary preparation window.

- Read a small React component.
- Predict behavior before executing it.
- Identify semantic defects.
- Modify it while explaining the reasoning.
- AI may review only after Federico commits to a first solution.

### Boss 2: Final Rehearsal

Purpose: verify retention the morning of the interview.

- Active recall, not rereading.
- Story retrieval in random order.
- A 20–30 minute mixed-language simulation.
- Corrections only for the top remaining gaps.

## 6. Difficulty Engine

Each difficult mission follows this loop:

1. **Free response:** commit to an explanation before seeing hints or options.
2. **New constraint:** scale, latency, security, delivery time, accessibility, or user impact changes.
3. **Counterargument:** the interviewer presents a plausible competing design.
4. **Evidence:** connect the decision to experience, measurement, or a verification plan.
5. **Transfer:** solve a different surface form in React, Vue, or English.

Question formats rotate to prevent pattern learning:

- Explain and defend.
- Code forensics.
- Architecture fork with multiple reasonable answers.
- Incident room with incomplete information.
- Story cross-examination.
- Counterfactual constraints.
- Ranking or classification that requires justification.
- Unexpected language switch.

Multiple choice is secondary, never the default. When used:

- The player first gives an independent answer or explanation.
- Distractors are technically plausible and homogeneous in length and detail.
- Correct positions are balanced.
- Selecting an option without justification cannot pass.
- The rubric remains hidden until the attempt is locked.

Long answers, jargon, and keyword matching do not earn points by themselves.

## 7. Answer Frameworks

### Technical concepts

**Definition → when to use it → trade-off → real example**

The grill adds:

- Boundary where the definition stops being true.
- Alternative and selection criteria.
- Failure mode and validation.
- Vue-to-React semantic difference.

### Experience

**Context → problem → decision → rejected alternative → result → learning**

The grill adds:

- What Federico personally owned.
- What evidence was available at the time.
- What went worse than expected.
- What would fail at greater scale.
- What he would do differently now.

### Hypothetical problems

**Clarify requirements → identify risks → simplest viable solution → failure cases → testing and measurement**

The grill changes a constraint after the initial answer and requires the design to adapt without discarding valid earlier reasoning.

## 8. Story Forge

### Initial bank

Four deep stories:

1. Feature delivery and measurable impact.
2. Difficult bug, incident, or performance investigation.
3. Architecture, refactor, or migration decision.
4. Cross-functional disagreement, ambiguity, or alignment.

Two supporting examples:

5. Mistake and continuous improvement.
6. AI-assisted engineering, including delegation, validation, security, and accountability.

### Story Card fields

- Title and tags.
- System, users, scale, and constraints.
- Problem and business/user consequence.
- Federico's personal responsibility.
- Decision and reasoning.
- Strongest rejected alternative and trade-off.
- Observable evidence or explicitly unavailable metric.
- Failure cases and validation.
- Result.
- Learning and what would change today.
- Vue implementation context.
- React Bridge: same engineering decision in React terms.
- 30-second, 90-second, and deep-dive versions.
- English version.
- Hostile follow-up bank.
- Evidence confidence: verified, remembered but unmeasured, or incomplete.

The system never invents metrics, decisions, or ownership. Missing evidence becomes a question or an explicit limitation.

## 9. Mastery System

The score remains hidden during an attempt.

| Dimension | Weight |
|---|---:|
| Technical accuracy | 25% |
| Decisions and trade-offs | 20% |
| Ownership and seniority | 20% |
| Evidence and stories | 15% |
| Problem solving and validation | 10% |
| Bilingual communication | 10% |

### Gates

- Regular level: 75/100.
- Boss: 80/100.
- No critical dimension below 65.
- A response must survive two meaningful follow-ups.
- A hint caps the score for that attempt; mastery requires a later unassisted transfer attempt.
- XP is a visible progress and motivation signal only. It never substitutes for mastery, changes the rubric, or unlocks a boss after a failed gate.

### Positive signals

- Asking a clarification that materially affects the design.
- Calibrating uncertainty and explaining how to validate it.
- Comparing plausible alternatives.
- Connecting Vue, React, and real experience.
- Correcting the answer precisely when new evidence appears.

### Red flags

- Fabricated experience, metrics, or certainty.
- Naming tools without explaining the problem they solve.
- Treating Vue mutation semantics as React state semantics.
- Hiding personal contribution behind “we.”
- Using AI without a validation and accountability model.
- Producing a memorized answer that fails under a changed constraint.

## 10. Bilingual Behavior

- Instruction and corrective teaching may use Spanish.
- Technical questions are primarily Spanish during levels.
- English switches are unpredictable and become more frequent near bosses.
- Introductory pitch, recent-experience explanation, and at least two deep stories exist in both languages.
- Accent is not scored. Structure, intelligibility, and preserved technical precision are scored.
- The rubric does not change with language.

## 11. Schedule

### Today: 240 minutes

| Segment | Minutes |
|---|---:|
| Calibration Gate | 15 |
| Framework Translator | 35 |
| State Strategist | 30 |
| Break | 10 |
| Architecture Guardian | 30 |
| Story Forge | 45 |
| Break | 10 |
| Boss 1 | 30 |
| Technical Challenge Prologue | 25 |
| Gap Log and save point | 10 |

The diagnostic may move up to 15 minutes from the Challenge Prologue or a mastered story to the highest-risk gap.

### Tomorrow

- 08:00–08:45: breakfast, shower, and movement.
- 08:45–09:15: active Vue-to-React recall.
- 09:15–09:25: break.
- 09:25–10:05: random Story Card recall.
- 10:05–10:20: break.
- 10:20–10:50: Boss 2.
- 10:50–11:10: correct only the top remaining gaps.
- 11:10: mandatory study stop.
- 11:10–12:30: light food, walk, equipment check, and recovery.
- 12:30: interview.

## 12. Runtime Architecture

The game runs inside the current Codex task at localhost.

### Localhost interface

- Displays the current mission without leaking the answer.
- Displays timer, mode, language, XP, mastery, Story Cards, Gap Log, and unlocks.
- Hosts interactive selections, rankings, code-forensics controls, and navigation.
- Shows feedback only after the attempt is closed.
- Reads the newest screen produced for the active session.

### Codex task

- Generates questions and constraint variants.
- Conducts the grill and bilingual follow-ups.
- Interprets open-ended answers.
- Applies the hidden rubric.
- Extracts Story Cards without fabricating facts.
- Chooses remediation and the next mission.
- Writes updated localhost screens and local progress state.

### Local state

- Session identity and current level.
- Attempts, hints, follow-ups, and scores.
- Story Cards and evidence confidence.
- Gap Log and mastery per concept.
- Timer checkpoints and resume point.

No external AI API, API key, cloud database, login, or separate AI service is part of this design.

### Interaction model

The selected model is mixed:

- Open-ended answers and story narration happen in the Codex chat so the answer immediately creates the next agent turn.
- Localhost handles choices, ranking, code forensics, timers, and game-state visualization.
- Browser events are consumed on the next chat turn.

## 13. Module Boundaries

- **Curriculum:** levels, objectives, React/Vue knowledge map, and trusted source links.
- **Session Director:** mode, language, time budget, difficulty, and mission selection.
- **Challenge Engine:** scenario seeds, variants, constraints, and follow-up strategies.
- **Evaluator:** hidden rubric, red flags, confidence, mastery, and remediation.
- **Story Vault:** evidence, story versions, React Bridge, and cross-examination history.
- **Progress:** attempts, gaps, retention, unlocks, and resume state.
- **Localhost Presenter:** visual state and browser events; it contains no interview judgment.

The question generator and evaluator use the same immutable rubric for an attempt, but the player-facing question never receives the answer key.

## 14. Data Flow

1. Session Director selects a level objective and scenario seed.
2. Challenge Engine creates a prompt, hidden rubric, constraints, and follow-up strategy.
3. Localhost presents the mission without rubric leakage.
4. Federico commits an answer in chat or an interaction in localhost.
5. Codex asks up to two targeted follow-ups.
6. Evaluator scores only when evidence is sufficient.
7. Story Vault or Gap Log receives the structured outcome.
8. Progress applies the mastery gate.
9. Session Director chooses a transfer variant, remediation, or unlock.
10. Localhost receives the next screen.

## 15. Error Handling and Safety

- **Insufficient evaluation evidence:** ask a targeted follow-up or mark the attempt for review; do not invent a score.
- **Question leaks the expected answer:** discard the question without scoring and generate a new surface form.
- **Ambiguous user statement:** separate factual uncertainty from technical reasoning before evaluation.
- **Missing story evidence:** mark it incomplete or unmeasured; never generate a metric.
- **Sensitive company information:** request anonymization and preserve only the minimum technical context.
- **Server interruption:** persist a resume point and restart the localhost companion on the same project and port when possible.
- **Time overrun:** save the current attempt and enforce the next break or the mandatory stop.
- **Model inconsistency:** replay the scenario seed and immutable rubric; if unresolved, use an unscored transfer check.

## 16. Verification Strategy

### Content checks

- React/Vue claims are traceable to official documentation.
- Questions contain no accidental answer cues.
- Distractors are plausible and similar in length/detail.
- Correct option positions remain balanced across a pack.
- Keyword-only answers fail reasoning criteria.
- Each important concept has at least two different surface forms.

### Behavior checks

- Coach and Interview feedback cannot leak into each other.
- Hints cap the current attempt and are recorded.
- Mastery gates block a critical red dimension.
- Language switching preserves the rubric.
- Timers, pause, resume, and mandatory stop behave consistently.
- Browser interactions are consumed once.
- Story import/export or local reload preserves evidence and versions.

### Acceptance journey

1. Start a fresh session and complete Calibration Gate.
2. Fail a question with a plausible but incomplete answer.
3. Receive a targeted Coach remediation without seeing a canned answer first.
4. Pass a different transfer scenario unassisted.
5. Create one Story Card through grilling and reject a fabricated metric.
6. Enter Interview Mode and verify that feedback stays hidden.
7. Complete two follow-ups, receive the score, and update the Gap Log.
8. Resume the session after a localhost restart.

## 17. Success Criteria for Tomorrow

- Complete four deep Story Cards and two supporting examples.
- Explain the core Vue-to-React semantic differences without notes.
- Correctly allocate state across local state, Context, Redux, and TanStack Query.
- Explain Effects, cleanup, race conditions, and stale closures.
- Defend testing, performance, debugging, and architecture decisions with trade-offs.
- Complete Boss 1 and Boss 2 at 80/100 or higher with no critical dimension below 65.
- Deliver the introduction and at least two stories in English without losing technical meaning.
- Stop studying by 11:10 and enter the interview rested.
