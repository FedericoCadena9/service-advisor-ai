import type { AdvisorRunResponse } from './generated/types.gen'
import { decideAdvisorRunAdvisorRunsRunIdDecisionPost, startAdvisorRunAdvisorRunsPost } from './generated/sdk.gen'
import { requestFailed } from './failure'

export async function startAdvisorRun(token: string): Promise<AdvisorRunResponse> {
  const response = await startAdvisorRunAdvisorRunsPost({ headers: { authorization: `Bearer ${token}` } })
  if (!('data' in response) || !response.data) throw requestFailed('Advisor run unavailable', response)
  return response.data
}

export async function decideAdvisorRun(token: string, runId: string): Promise<AdvisorRunResponse> {
  const response = await decideAdvisorRunAdvisorRunsRunIdDecisionPost({ body: { decision: 'approve' }, headers: { authorization: `Bearer ${token}` }, path: { run_id: runId } })
  if (!('data' in response) || !response.data) throw requestFailed('Advisor decision unavailable', response)
  return response.data
}

export async function fetchAdvisorRunEvents(token: string, runId: string): Promise<string[]> {
  const response = await fetch(
    `${import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'}/advisor-runs/${runId}/events`,
    { headers: { authorization: `Bearer ${token}` } },
  )
  if (!response.ok) throw requestFailed('Advisor run event stream unavailable', { response: { status: response.status } })
  return (await response.text())
    .split('\n')
    .filter((line) => line.startsWith('data: '))
    .map((line) => line.slice('data: '.length))
}
