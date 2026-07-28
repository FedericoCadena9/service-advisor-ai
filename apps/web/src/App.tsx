import { type FormEvent, useEffect, useState } from 'react'

import { enterDemoWorkspace } from './api/demo-session'
import type {
  CreateDemoSessionRequest,
  VehicleSearchResponse,
  WorkspaceResponse,
} from './api/generated/types.gen'
import { fetchHealth } from './api/health'
import { searchDemoVehicles } from './api/vehicles'

type HealthState = 'loading' | 'healthy' | 'unavailable'

export default function App() {
  const [state, setState] = useState<HealthState>('loading')
  const [workspace, setWorkspace] = useState<WorkspaceResponse | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [vehicles, setVehicles] = useState<VehicleSearchResponse[]>([])
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
      const session = await enterDemoWorkspace(role)
      setToken(session.token)
      setWorkspace(session.workspace)
    } catch {
      setSessionError('Demo session unavailable')
    }
  }

  async function searchVehicles(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!token || !query.trim()) return

    try {
      setVehicles(await searchDemoVehicles(token, query))
    } catch {
      setSessionError('Vehicle search unavailable')
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
          <form onSubmit={searchVehicles} role="search">
            <label htmlFor="vehicle-search">Search demo vehicle</label>
            <input
              id="vehicle-search"
              name="vehicle-search"
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
            <button type="submit">Search</button>
          </form>
          <ul aria-label="Vehicle search results">
            {vehicles.map((vehicle) => (
              <li key={vehicle.id}>{`${vehicle.vehicle_label} — Demo data`}</li>
            ))}
          </ul>
        </section>
      )}
      {sessionError && <p role="alert">{sessionError}</p>}
    </main>
  )
}
