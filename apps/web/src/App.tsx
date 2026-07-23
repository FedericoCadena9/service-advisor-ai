import { useEffect, useState } from 'react'

import { fetchHealth } from './api/health'

type HealthState = 'loading' | 'healthy' | 'unavailable'

export default function App() {
  const [state, setState] = useState<HealthState>('loading')

  useEffect(() => {
    fetchHealth()
      .then(() => setState('healthy'))
      .catch(() => setState('unavailable'))
  }, [])

  const message =
    state === 'healthy'
      ? 'Demo environment healthy'
      : state === 'unavailable'
        ? 'Demo environment unavailable'
        : 'Checking demo environment'

  return (
    <main>
      <h1>Service Advisor AI</h1>
      <p role="status">{message}</p>
    </main>
  )
}
