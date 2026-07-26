import { useEffect, useReducer } from 'react'

import { gameReducer, type GameAction } from '../domain/game'
import { loadGameState, saveGameState } from '../domain/storage'

export function useGame(): [ReturnType<typeof loadGameState>, React.Dispatch<GameAction>] {
  const [state, dispatch] = useReducer(gameReducer, undefined, () =>
    loadGameState(window.localStorage),
  )

  useEffect(() => {
    saveGameState(window.localStorage, state)
  }, [state])

  return [state, dispatch]
}
