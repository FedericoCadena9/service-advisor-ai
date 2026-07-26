import { describe, expect, it } from 'vitest'

import {
  createInitialGameState,
  gameReducer,
  getAdaptiveAllocation,
  getMissionScore,
  type EvaluationResult,
  type RubricScores,
} from './game'

const evaluation = (
  scores: RubricScores,
  overrides: Partial<EvaluationResult> = {},
): EvaluationResult => ({
  scores,
  followUpCount: 2,
  hintUsed: false,
  unassistedTransfer: true,
  evidenceSummary: 'La respuesta conectó decisión, alternativa y verificación.',
  attemptClosed: true,
  ...overrides,
})

const passingLevel: RubricScores = {
  technicalAccuracy: 80,
  tradeoffs: 80,
  ownership: 80,
  evidence: 80,
  problemSolving: 80,
  bilingualCommunication: 80,
}

const passingBoss: RubricScores = {
  technicalAccuracy: 84,
  tradeoffs: 80,
  ownership: 82,
  evidence: 78,
  problemSolving: 80,
  bilingualCommunication: 86,
}

describe('game progression', () => {
  it('only exposes the calibration gate for a new player', () => {
    const state = createInitialGameState()

    expect(state.missions.calibration.status).toBe('available')
    expect(state.missions.bridge.status).toBe('locked')
    expect(state.activeMissionId).toBe('calibration')
  })

  it('starts an available mission without mutating the previous state', () => {
    const initial = createInitialGameState()
    const started = gameReducer(initial, {
      type: 'mission_started',
      missionId: 'calibration',
    })

    expect(started).not.toBe(initial)
    expect(initial.missions.calibration.status).toBe('available')
    expect(started.missions.calibration.status).toBe('active')
  })

  it('weights technical accuracy at 25 percent', () => {
    expect(
      getMissionScore({
        technicalAccuracy: 100,
        tradeoffs: 0,
        ownership: 0,
        evidence: 0,
        problemSolving: 0,
        bilingualCommunication: 0,
      }),
    ).toBe(25)
  })

  it('passes a level at 75 and unlocks the next mission', () => {
    const initial = createInitialGameState()
    const passed = gameReducer(initial, {
      type: 'attempt_scored',
      missionId: 'calibration',
      evaluation: evaluation(passingLevel),
    })

    expect(passed.missions.calibration.status).toBe('passed')
    expect(passed.missions.bridge.status).toBe('available')
    expect(passed.attempts).toHaveLength(1)
  })

  it('requires 80 to pass a boss', () => {
    let state = createInitialGameState()
    for (const missionId of ['calibration', 'bridge', 'rendering', 'architecture', 'story_forge'] as const) {
      state = gameReducer(state, {
        type: 'attempt_scored',
        missionId,
        evaluation: evaluation(passingLevel),
      })
    }

    const retry = gameReducer(state, {
      type: 'attempt_scored',
      missionId: 'knowledge_boss',
      evaluation: evaluation({ ...passingLevel, technicalAccuracy: 76 }),
    })
    expect(retry.missions.knowledge_boss.status).toBe('retry')

    const passed = gameReducer(retry, {
      type: 'attempt_scored',
      missionId: 'knowledge_boss',
      evaluation: evaluation(passingBoss),
    })
    expect(passed.missions.knowledge_boss.status).toBe('passed')
    expect(passed.missions.challenge.status).toBe('available')
  })

  it('does not pass when one critical dimension is below 65', () => {
    const state = gameReducer(createInitialGameState(), {
      type: 'attempt_scored',
      missionId: 'calibration',
      evaluation: evaluation({
        technicalAccuracy: 95,
        tradeoffs: 95,
        ownership: 64,
        evidence: 95,
        problemSolving: 95,
        bilingualCommunication: 95,
      }),
    })

    expect(getMissionScore(state.attempts[0].scores)).toBeGreaterThan(75)
    expect(state.missions.calibration.status).toBe('retry')
    expect(state.missions.bridge.status).toBe('locked')
  })

  it('keeps the best score while preserving every retry attempt', () => {
    const failed = gameReducer(createInitialGameState(), {
      type: 'attempt_scored',
      missionId: 'calibration',
      evaluation: evaluation({ ...passingLevel, ownership: 50 }),
    })
    const recovered = gameReducer(failed, {
      type: 'attempt_scored',
      missionId: 'calibration',
      evaluation: evaluation(passingLevel),
    })

    expect(recovered.attempts).toHaveLength(2)
    expect(recovered.missions.calibration.bestScore).toBe(80)
    expect(recovered.missions.calibration.status).toBe('passed')
  })

  it('does not revoke a completed mission after a weaker practice retry', () => {
    const passed = gameReducer(createInitialGameState(), {
      type: 'attempt_scored',
      missionId: 'calibration',
      evaluation: evaluation(passingLevel),
    })
    const practiced = gameReducer(passed, {
      type: 'attempt_scored',
      missionId: 'calibration',
      evaluation: evaluation({ ...passingLevel, ownership: 50 }),
    })

    expect(practiced.missions.calibration.status).toBe('passed')
    expect(practiced.missions.calibration.bestScore).toBe(80)
    expect(practiced.missions.bridge.status).toBe('available')
  })

  it('allocates a 15-minute drill to the weakest accumulated dimension', () => {
    let state = gameReducer(createInitialGameState(), {
      type: 'attempt_scored',
      missionId: 'calibration',
      evaluation: evaluation({ ...passingLevel, evidence: 66 }),
    })
    state = gameReducer(state, {
      type: 'attempt_scored',
      missionId: 'calibration',
      evaluation: evaluation({ ...passingLevel, evidence: 68 }),
    })

    expect(getAdaptiveAllocation(state)).toEqual({
      dimension: 'evidence',
      minutes: 15,
      average: 67,
    })
  })

  it('requires two follow-ups and an unassisted transfer even with high scores', () => {
    const oneFollowUp = gameReducer(createInitialGameState(), {
      type: 'attempt_scored',
      missionId: 'calibration',
      evaluation: evaluation(passingLevel, { followUpCount: 1 }),
    })
    expect(oneFollowUp.missions.calibration.status).toBe('retry')

    const assisted = gameReducer(createInitialGameState(), {
      type: 'attempt_scored',
      missionId: 'calibration',
      evaluation: evaluation(passingLevel, { hintUsed: true }),
    })
    expect(assisted.missions.calibration.status).toBe('retry')

    const noTransfer = gameReducer(createInitialGameState(), {
      type: 'attempt_scored',
      missionId: 'calibration',
      evaluation: evaluation(passingLevel, { unassistedTransfer: false }),
    })
    expect(noTransfer.missions.calibration.status).toBe('retry')
  })
})
