export const MISSION_SEQUENCE = [
  'calibration',
  'bridge',
  'rendering',
  'architecture',
  'story_forge',
  'knowledge_boss',
  'challenge',
  'final_boss',
] as const

export type MissionId = (typeof MISSION_SEQUENCE)[number]
export type MissionKind = 'level' | 'boss'
export type MissionStatus = 'locked' | 'available' | 'active' | 'retry' | 'passed'
export type Language = 'es' | 'en'
export type GameMode = 'coach' | 'interview'

export const RUBRIC_DIMENSIONS = [
  'technicalAccuracy',
  'tradeoffs',
  'ownership',
  'evidence',
  'problemSolving',
  'bilingualCommunication',
] as const

export type RubricDimension = (typeof RUBRIC_DIMENSIONS)[number]
export type RubricScores = Record<RubricDimension, number>

export type EvaluationResult = {
  scores: RubricScores
  followUpCount: number
  hintUsed: boolean
  unassistedTransfer: boolean
  evidenceSummary: string
  attemptClosed: true
}

export type MissionProgress = {
  status: MissionStatus
  bestScore: number | null
  attempts: number
}

export type Attempt = {
  id: string
  missionId: MissionId
  score: number
  scores: RubricScores
  passed: boolean
  followUpCount: number
  hintUsed: boolean
  unassistedTransfer: boolean
  evidenceSummary: string
}

export type Story = {
  id: string
  title: string
  context: string
  problem: string
  decision: string
  rejectedAlternative: string
  result: string
  learning: string
  personalOwnership: string
  scaleConstraints: string
  consequence: string
  evidence: string
  evidenceConfidence: 'verified' | 'remembered_unmeasured' | 'incomplete'
  failureValidation: string
  vueContext: string
  reactBridge: string
  version30: string
  version90: string
  deepDive: string
  englishVersion: string
  tags: string
  hostileFollowUps: string
}

export type GameState = {
  language: Language
  mode: GameMode
  activeMissionId: MissionId
  missions: Record<MissionId, MissionProgress>
  attempts: Attempt[]
  stories: Story[]
}

export type GameAction =
  | { type: 'language_set'; language: Language }
  | { type: 'mode_set'; mode: GameMode }
  | { type: 'mission_selected'; missionId: MissionId }
  | { type: 'mission_started'; missionId: MissionId }
  | { type: 'attempt_scored'; missionId: MissionId; evaluation: EvaluationResult }
  | { type: 'story_saved'; story: Omit<Story, 'id'> }
  | { type: 'game_reset' }

const MISSION_KINDS: Record<MissionId, MissionKind> = {
  calibration: 'level',
  bridge: 'level',
  rendering: 'level',
  architecture: 'level',
  knowledge_boss: 'boss',
  story_forge: 'level',
  challenge: 'level',
  final_boss: 'boss',
}

const emptyMission = (status: MissionStatus): MissionProgress => ({
  status,
  bestScore: null,
  attempts: 0,
})

export function createInitialGameState(): GameState {
  return {
    language: 'es',
    mode: 'coach',
    activeMissionId: 'calibration',
    missions: {
      calibration: emptyMission('available'),
      bridge: emptyMission('locked'),
      rendering: emptyMission('locked'),
      architecture: emptyMission('locked'),
      knowledge_boss: emptyMission('locked'),
      story_forge: emptyMission('locked'),
      challenge: emptyMission('locked'),
      final_boss: emptyMission('locked'),
    },
    attempts: [],
    stories: [],
  }
}

export function getMissionScore(scores: RubricScores): number {
  return Math.round(
    scores.technicalAccuracy * 0.25 +
      scores.tradeoffs * 0.2 +
      scores.ownership * 0.2 +
      scores.evidence * 0.15 +
      scores.problemSolving * 0.1 +
      scores.bilingualCommunication * 0.1,
  )
}

export function isPassingAttempt(
  missionId: MissionId,
  evaluation: EvaluationResult,
): boolean {
  const { scores } = evaluation
  const threshold = MISSION_KINDS[missionId] === 'boss' ? 80 : 75
  const clearsCriticalFloor = RUBRIC_DIMENSIONS.every(
    (dimension) => scores[dimension] >= 65,
  )
  return (
    evaluation.attemptClosed &&
    evaluation.followUpCount >= 2 &&
    !evaluation.hintUsed &&
    evaluation.unassistedTransfer &&
    clearsCriticalFloor &&
    getMissionScore(scores) >= threshold
  )
}

export function getEvaluationScore(evaluation: EvaluationResult): number {
  const rawScore = getMissionScore(evaluation.scores)
  return evaluation.hintUsed ? Math.min(rawScore, 74) : rawScore
}

function scoreAttempt(
  state: GameState,
  missionId: MissionId,
  evaluation: EvaluationResult,
): GameState {
  const current = state.missions[missionId]
  if (current.status === 'locked') return state

  const { scores } = evaluation
  const score = getEvaluationScore(evaluation)
  const passed = isPassingAttempt(missionId, evaluation)
  const remainsPassed = current.status === 'passed'
  const attempt: Attempt = {
    id: `attempt-${state.attempts.length + 1}`,
    missionId,
    score,
    scores: { ...scores },
    passed,
    followUpCount: evaluation.followUpCount,
    hintUsed: evaluation.hintUsed,
    unassistedTransfer: evaluation.unassistedTransfer,
    evidenceSummary: evaluation.evidenceSummary,
  }
  const missions = {
    ...state.missions,
    [missionId]: {
      status: passed || remainsPassed ? ('passed' as const) : ('retry' as const),
      attempts: current.attempts + 1,
      bestScore: Math.max(current.bestScore ?? 0, score),
    },
  }

  let activeMissionId = missionId
  if (passed) {
    const currentIndex = MISSION_SEQUENCE.indexOf(missionId)
    const nextMissionId = MISSION_SEQUENCE[currentIndex + 1]
    if (nextMissionId) {
      activeMissionId = nextMissionId
      if (missions[nextMissionId].status === 'locked') {
        missions[nextMissionId] = {
          ...missions[nextMissionId],
          status: 'available',
        }
      }
    }
  }

  return {
    ...state,
    activeMissionId,
    missions,
    attempts: [...state.attempts, attempt],
  }
}

export function gameReducer(state: GameState, action: GameAction): GameState {
  switch (action.type) {
    case 'language_set':
      return { ...state, language: action.language }
    case 'mode_set':
      return { ...state, mode: action.mode }
    case 'mission_selected':
      return state.missions[action.missionId].status === 'locked'
        ? state
        : { ...state, activeMissionId: action.missionId }
    case 'mission_started': {
      const mission = state.missions[action.missionId]
      if (mission.status !== 'available' && mission.status !== 'retry') return state
      return {
        ...state,
        activeMissionId: action.missionId,
        missions: {
          ...state.missions,
          [action.missionId]: { ...mission, status: 'active' },
        },
      }
    }
    case 'attempt_scored':
      return scoreAttempt(state, action.missionId, action.evaluation)
    case 'story_saved':
      return {
        ...state,
        stories: [
          ...state.stories,
          { ...action.story, id: `story-${state.stories.length + 1}` },
        ],
      }
    case 'game_reset':
      return createInitialGameState()
  }
}

export function getMastery(state: GameState): Record<RubricDimension, number> {
  return RUBRIC_DIMENSIONS.reduce<Record<RubricDimension, number>>(
    (mastery, dimension) => {
      if (state.attempts.length === 0) {
        mastery[dimension] = 0
        return mastery
      }
      const total = state.attempts.reduce(
        (sum, attempt) => sum + attempt.scores[dimension],
        0,
      )
      mastery[dimension] = Math.round(total / state.attempts.length)
      return mastery
    },
    {
      technicalAccuracy: 0,
      tradeoffs: 0,
      ownership: 0,
      evidence: 0,
      problemSolving: 0,
      bilingualCommunication: 0,
    },
  )
}

export function getAdaptiveAllocation(state: GameState): {
  dimension: RubricDimension
  minutes: 15
  average: number
} | null {
  if (state.attempts.length === 0) return null
  const mastery = getMastery(state)
  const dimension = RUBRIC_DIMENSIONS.reduce((weakest, candidate) =>
    mastery[candidate] < mastery[weakest] ? candidate : weakest,
  )
  return { dimension, minutes: 15, average: mastery[dimension] }
}
