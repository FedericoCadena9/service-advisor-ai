import { type FormEvent, useCallback, useEffect, useState } from 'react'

import { fetchQualityDashboard } from './api/dashboard'
import type { AdvisorContext } from './api/advisor-context'
import { QualityDashboard } from './components/advisor/QualityDashboard'

import { saveCheckin } from './api/checkins'
import { enterDemoWorkspace } from './api/demo-session'
import type {
  CreateDemoSessionRequest,
  VehicleSearchResponse,
  WorkspaceResponse,
} from './api/generated/types.gen'
import { fetchHealth } from './api/health'
import { searchDemoVehicles } from './api/vehicles'
import { fetchRecommendation } from './api/recommendations'
import { askContextualChat } from './api/chat'
import { decideAdvisorRun, fetchAdvisorRunEvents, startAdvisorRun } from './api/advisor-run'
import { draftQuote } from './api/quotes'
import { decideQuoteReview, openQuoteReview } from './api/quote-reviews'
import { advanceMessage, previewSms, reserveAppointment, sendSms } from './api/messaging'
import { askServiceQuestion } from './api/service-questions'
import { confirmTranscript, recordVoiceNote } from './api/voice'
import { VoiceCheckinPanel } from './components/advisor/VoiceCheckinPanel'
import { RecommendationConsole } from './components/advisor/RecommendationConsole'

type HealthState = 'loading' | 'waking' | 'healthy' | 'unavailable'

const COLD_START_RETRY_MS = 400
const DEMO_VEHICLE_ID = 'honda-civic-2019-lx'

export default function App() {
  const [state, setState] = useState<HealthState>('loading')
  const [workspace, setWorkspace] = useState<WorkspaceResponse | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [vehicles, setVehicles] = useState<VehicleSearchResponse[]>([])
  const [checkinMileage, setCheckinMileage] = useState('')
  const [useProfile, setUseProfile] = useState<'normal' | 'severe'>('normal')
  const [severeUseFactors, setSevereUseFactors] = useState('')
  const [concern, setConcern] = useState('')
  const [appointmentWindow, setAppointmentWindow] = useState('')
  const [messageConsent, setMessageConsent] = useState(false)
  const [checkinSaved, setCheckinSaved] = useState(false)
  const [recommendation, setRecommendation] = useState<import('./api/generated/types.gen').RecommendationResponse>()
  const [advisorRunId, setAdvisorRunId] = useState<string | null>(null)
  const [traceId, setTraceId] = useState<string | null>(null)
  const [vehicleId, setVehicleId] = useState(DEMO_VEHICLE_ID)
  const [voiceNoteId, setVoiceNoteId] = useState<string | null>(null)
  const requireToken = useCallback(() => {
    if (!token) throw new Error('Session required')
    return token
  }, [token])
  const advisorContext = useCallback(
    (): AdvisorContext => ({
      vehicleId,
      currentMileageKm: Number(checkinMileage) || 0,
      traceId,
    }),
    [vehicleId, checkinMileage, traceId],
  )
  const loadDashboard = useCallback(
    async () => fetchQualityDashboard(requireToken()),
    [requireToken],
  )
  const [sessionError, setSessionError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    // The public demo scales to zero, so the first probe may hit a cold start.
    async function probeHealth() {
      try {
        await fetchHealth()
        if (!cancelled) setState('healthy')
      } catch {
        if (cancelled) return
        setState('waking')
        await new Promise((resolve) => setTimeout(resolve, COLD_START_RETRY_MS))
        if (cancelled) return
        try {
          await fetchHealth()
          if (!cancelled) setState('healthy')
        } catch {
          if (!cancelled) setState('unavailable')
        }
      }
    }

    void probeHealth()
    return () => {
      cancelled = true
    }
  }, [])

  const message = {
    healthy: 'Demo environment healthy',
    unavailable: 'Demo environment unavailable',
    waking: 'Waking the demo environment after scale to zero',
    loading: 'Checking demo environment',
  }[state]

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

  async function submitCheckin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!token) return

    try {
      await saveCheckin(token, {
        current_mileage_km: Number(checkinMileage),
        checked_in_on: new Date().toISOString().slice(0, 10),
        use_profile: useProfile,
        severe_use_factors: severeUseFactors
          .split(',')
          .map((factor) => factor.trim())
          .filter(Boolean),
        concern,
        appointment_window: appointmentWindow,
        message_consent: messageConsent,
        voice_note_id: voiceNoteId,
      })
      setCheckinSaved(true)
      setRecommendation(await fetchRecommendation(token, advisorContext()))
    } catch {
      setSessionError('Check-in could not be saved')
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
              <li key={vehicle.id}>
                <button type="button" onClick={() => setVehicleId(vehicle.id)}>
                  {`${vehicle.vehicle_label} — Demo data`}
                </button>
              </li>
            ))}
          </ul>
          <form onSubmit={submitCheckin} aria-labelledby="checkin-heading">
            <h3 id="checkin-heading">Vehicle check-in</h3>
            <VoiceCheckinPanel
              onRecord={async (note) => recordVoiceNote(requireToken(), note)}
              onConfirm={async (noteId, transcript) => confirmTranscript(requireToken(), noteId, transcript)}
              onConfirmed={setVoiceNoteId}
            />
            <label htmlFor="current-mileage">Current mileage (km)</label>
            <input
              id="current-mileage"
              type="number"
              min="42500"
              required
              value={checkinMileage}
              onChange={(event) => setCheckinMileage(event.target.value)}
            />
            <label htmlFor="use-profile">Use profile</label>
            <select
              id="use-profile"
              value={useProfile}
              onChange={(event) => setUseProfile(event.target.value as 'normal' | 'severe')}
            >
              <option value="normal">Normal use</option>
              <option value="severe">Severe use</option>
            </select>
            <label htmlFor="severe-use-factors">Severe use factors</label>
            <input
              id="severe-use-factors"
              value={severeUseFactors}
              onChange={(event) => setSevereUseFactors(event.target.value)}
            />
            <label htmlFor="concern">Written concern</label>
            <textarea
              id="concern"
              required
              value={concern}
              onChange={(event) => setConcern(event.target.value)}
            />
            <label htmlFor="appointment-window">Desired appointment window</label>
            <input
              id="appointment-window"
              required
              value={appointmentWindow}
              onChange={(event) => setAppointmentWindow(event.target.value)}
            />
            <label htmlFor="message-consent">Consent to prepare a message</label>
            <input
              id="message-consent"
              type="checkbox"
              checked={messageConsent}
              onChange={(event) => setMessageConsent(event.target.checked)}
            />
            <button type="submit">Confirm check-in</button>
          </form>
          {checkinSaved && <p role="status">Check-in confirmed</p>}
          <RecommendationConsole recommendation={recommendation} onStartRun={async () => { const activeToken = requireToken(); const run = await startAdvisorRun(activeToken); setAdvisorRunId(run.id); setTraceId(run.trace_id); return { id: run.id, events: await fetchAdvisorRunEvents(activeToken, run.id) } }} onApproveRun={async () => { const activeToken = requireToken(); if (!advisorRunId) throw new Error('Run required'); await decideAdvisorRun(activeToken, advisorRunId) }} onAsk={async (question) => (await askContextualChat(requireToken(), question, advisorContext())).text} onDraftQuote={async (serviceCodes) => draftQuote(requireToken(), serviceCodes, advisorContext())} onOpenReview={async (serviceCodes) => openQuoteReview(requireToken(), serviceCodes, advisorContext())} onDecideReview={async (reviewId, decision, reason) => decideQuoteReview(requireToken(), reviewId, decision, { idempotencyKey: reviewId, reason, context: advisorContext() })} onAskData={async (question) => askServiceQuestion(requireToken(), question)} timeline={{ onReserve: async (quoteId) => reserveAppointment(requireToken(), quoteId), onPreview: async (quoteId) => previewSms(requireToken(), quoteId), onSend: async (quoteId, text) => sendSms(requireToken(), quoteId, text), onAdvance: async (deliveryId) => advanceMessage(requireToken(), deliveryId) }} />
          {(workspace.role === 'manager' || workspace.role === 'admin') && (
            <QualityDashboard onLoad={loadDashboard} />
          )}
        </section>
      )}
      {sessionError && <p role="alert">{sessionError}</p>}
    </main>
  )
}
