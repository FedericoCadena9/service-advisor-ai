import { describe, expect, it } from 'vitest'

import { createInitialGameState, gameReducer } from './game'
import {
  STORAGE_KEY,
  clearGameState,
  loadGameState,
  saveGameState,
  type StorageLike,
} from './storage'

function memoryStorage(): StorageLike {
  const data = new Map<string, string>()
  return {
    getItem: (key) => data.get(key) ?? null,
    setItem: (key, value) => data.set(key, value),
    removeItem: (key) => data.delete(key),
  }
}

describe('game persistence', () => {
  it('round-trips a valid game state', () => {
    const storage = memoryStorage()
    const state = gameReducer(createInitialGameState(), {
      type: 'mode_set',
      mode: 'interview',
    })

    saveGameState(storage, state)

    expect(loadGameState(storage)).toEqual(state)
  })

  it('falls back safely when JSON is corrupt', () => {
    const storage = memoryStorage()
    storage.setItem(STORAGE_KEY, '{bad json')

    expect(loadGameState(storage)).toEqual(createInitialGameState())
  })

  it('falls back for unsupported or malformed schemas', () => {
    const storage = memoryStorage()
    storage.setItem(
      STORAGE_KEY,
      JSON.stringify({ schemaVersion: 99, state: createInitialGameState() }),
    )
    expect(loadGameState(storage)).toEqual(createInitialGameState())

    storage.setItem(
      STORAGE_KEY,
      JSON.stringify({ schemaVersion: 1, state: { mode: 'coach' } }),
    )
    expect(loadGameState(storage)).toEqual(createInitialGameState())
  })

  it('rejects corrupt nested attempts and stories', () => {
    const storage = memoryStorage()
    const initial = createInitialGameState()
    storage.setItem(
      STORAGE_KEY,
      JSON.stringify({ schemaVersion: 1, state: { ...initial, attempts: [{}] } }),
    )
    expect(loadGameState(storage)).toEqual(initial)

    storage.setItem(
      STORAGE_KEY,
      JSON.stringify({ schemaVersion: 1, state: { ...initial, stories: [null] } }),
    )
    expect(loadGameState(storage)).toEqual(initial)
  })

  it('clears stored progress', () => {
    const storage = memoryStorage()
    saveGameState(storage, createInitialGameState())

    clearGameState(storage)

    expect(storage.getItem(STORAGE_KEY)).toBeNull()
  })
})
