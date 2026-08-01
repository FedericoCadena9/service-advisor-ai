import type { DashboardResponse } from './generated/types.gen'
import { getQualityDashboardAdminDashboardGet } from './generated/sdk.gen'
import { requestFailed } from './failure'

export async function fetchQualityDashboard(token: string): Promise<DashboardResponse> {
  const response = await getQualityDashboardAdminDashboardGet({
    headers: { authorization: `Bearer ${token}` },
  })
  if (!('data' in response) || !response.data) throw requestFailed('Dashboard unavailable', response)
  return response.data
}
