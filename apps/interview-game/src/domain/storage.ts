import {
  MISSION_SEQUENCE,
  RUBRIC_DIMENSIONS,
  createInitialGameState,
  type GameState,
  type MissionStatus,
} from './game'

export const STORAGE_KEY = 'seniority-quest:game-state'
const SCHEMA_VERSION = 1

export type StorageLike = Pick<Storage, 'getItem' | 'setItem' | 'removeItem'>

type StoredGame = {
  schemaVersion: typeof SCHEMA_VERSION
  state: GameState
}

const missionStatuses: MissionStatus[] = [
  'locked',
  'available',
  'active',
  'retry',
  'passed',
]

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function isGameState(value: unknown): value is GameState {
  if (!isRecord(value) || !isRecord(value.missions)) return false
  const missions = value.missions
  if (value.language !== 'es' && value.language !== 'en') return false
  if (value.mode !== 'coach' && value.mode !== 'interview') return false
  if (!MISSION_SEQUENCE.includes(value.activeMissionId as never)) return false
  if (!Array.isArray(value.attempts) || !value.attempts.every(isAttempt)) return false
  if (!Array.isArray(value.stories) || !value.stories.every(isStory)) return false

  return MISSION_SEQUENCE.every((missionId) => {
    const mission = missions[missionId]
    return (
      isRecord(mission) &&
      missionStatuses.includes(mission.status as MissionStatus) &&
      typeof mission.attempts === 'number' &&
      (mission.bestScore === null || typeof mission.bestScore === 'number')
    )
  })
}

function isScore(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= 100
}

function isAttempt(value: unknown): boolean {
  if (!isRecord(value) || !isRecord(value.scores)) return false
  const scores = value.scores
  return (
    typeof value.id === 'string' &&
    MISSION_SEQUENCE.includes(value.missionId as never) &&
    isScore(value.score) &&
    typeof value.passed === 'boolean' &&
    typeof value.followUpCount === 'number' &&
    Number.isInteger(value.followUpCount) &&
    value.followUpCount >= 0 &&
    typeof value.hintUsed === 'boolean' &&
    typeof value.unassistedTransfer === 'boolean' &&
    typeof value.evidenceSummary === 'string' &&
    RUBRIC_DIMENSIONS.every((dimension) => isScore(scores[dimension]))
  )
}

function isStory(value: unknown): boolean {
  if (!isRecord(value)) return false
  return [
    'id',
    'title',
    'context',
    'problem',
    'decision',
    'rejectedAlternative',
    'result',
    'learning',
    'personalOwnership',
    'scaleConstraints',
    'consequence',
    'evidence',
    'evidenceConfidence',
    'failureValidation',
    'vueContext',
    'reactBridge',
    'version30',
    'version90',
    'deepDive',
    'englishVersion',
    'tags',
    'hostileFollowUps',
  ].every((field) => typeof value[field] === 'string')
}

export function saveGameState(storage: StorageLike, state: GameState): void {
  const payload: StoredGame = { schemaVersion: SCHEMA_VERSION, state }
  storage.setItem(STORAGE_KEY, JSON.stringify(payload))
}

export function loadGameState(storage: StorageLike): GameState {
  const fallback = createInitialGameState()
  try {
    const raw = storage.getItem(STORAGE_KEY)
    if (!raw) return fallback
    const payload: unknown = JSON.parse(raw)
    if (
      !isRecord(payload) ||
      payload.schemaVersion !== SCHEMA_VERSION ||
      !isGameState(payload.state)
    ) {
      return fallback
    }
    return payload.state
  } catch {
    return fallback
  }
}

export function clearGameState(storage: StorageLike): void {
  storage.removeItem(STORAGE_KEY)
}
