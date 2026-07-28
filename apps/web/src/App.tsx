import { useEffect, useState } from 'react'

import { enterDemoWorkspace } from './api/demo-session'
import type { CreateDemoSessionRequest, WorkspaceResponse } from './api/generated/types.gen'
import { fetchHealth } from './api/health'

type HealthState = 'loading' | 'healthy' | 'unavailable'

export default function App() {
  const [state, setState] = useState<HealthState>('loading')
  const [workspace, setWorkspace] = useState<WorkspaceResponse | null>(null)
  const [sessionError, setSessionError] = useState<string | null>(null)

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

  async function chooseRole(role: CreateDemoSessionRequest['role']) {
    setSessionError(null)

    try {
      setWorkspace(await enterDemoWorkspace(role))
    } catch {
      setSessionError('Demo session unavailable')
    }
  }

  return (
    <main>
      <h1>Service Advisor AI</h1>
      <p role="status">{message}</p>
      {state === 'healthy' && !workspace && (
        <section aria-labelledby="role-selection-heading">
          <h2 id="role-selection-heading">Choose your demo role</h2>
          <button onClick={() => void chooseRole('advisor')}>Enter as Advisor</button>
          <button onClick={() => void chooseRole('manager')}>Enter as Manager</button>
          <button onClick={() => void chooseRole('admin')}>Enter as Admin</button>
        </section>
      )}
      {workspace && (
        <section aria-labelledby="workspace-heading">
          <h2 id="workspace-heading">Protected demo workspace</h2>
          <p>{`Role: ${workspace.role}`}</p>
          <p>{`Shop: ${workspace.shop_id}`}</p>
        </section>
      )}
      {sessionError && <p role="alert">{sessionError}</p>}
    </main>
  )
}
