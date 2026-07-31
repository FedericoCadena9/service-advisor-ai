import { getQualityDashboardAdminDashboardGet } from './generated/sdk.gen'

export type QualityDashboard = {
  trace_count: number
  span_count: number
  spans_by_kind: Record<string, number>
  citation_rate: number
  p50_latency_ms: number
  p95_latency_ms: number
  total_cost_mxn: string
  escalation_outcomes: Record<string, number>
  evaluation_thresholds_met: boolean
  evaluation_score: number
}

export async function fetchQualityDashboard(token: string): Promise<QualityDashboard> {
  const response = await getQualityDashboardAdminDashboardGet({
    headers: { authorization: `Bearer ${token}` },
  })
  if (!('data' in response) || !response.data) throw new Error('Dashboard unavailable')
  return response.data as QualityDashboard
}
