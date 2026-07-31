import type { DashboardResponse } from './generated/types.gen'
import { getQualityDashboardAdminDashboardGet } from './generated/sdk.gen'

export async function fetchQualityDashboard(token: string): Promise<DashboardResponse> {
  const response = await getQualityDashboardAdminDashboardGet({
    headers: { authorization: `Bearer ${token}` },
  })
  if (!('data' in response) || !response.data) throw new Error('Dashboard unavailable')
  return response.data
}
