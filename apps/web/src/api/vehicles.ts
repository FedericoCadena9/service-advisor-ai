import type { VehicleSearchResponse } from './generated/types.gen'
import { searchVehiclesVehiclesSearchGet } from './generated/sdk.gen'
import { requestFailed } from './failure'

export async function searchDemoVehicles(
  token: string,
  query: string,
): Promise<VehicleSearchResponse[]> {
  const response = await searchVehiclesVehiclesSearchGet({
    headers: { authorization: `Bearer ${token}` },
    query: { query },
  })

  if (!('data' in response) || !response.data) {
    throw requestFailed('Vehicle search failed', response)
  }

  return response.data
}
