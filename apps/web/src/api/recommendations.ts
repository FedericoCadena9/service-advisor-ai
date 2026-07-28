import type { RecommendationResponse } from './generated/types.gen'
import { getRecommendationVehiclesVehicleIdRecommendationGet } from './generated/sdk.gen'

export async function fetchRecommendation(token: string): Promise<RecommendationResponse> {
  const response = await getRecommendationVehiclesVehicleIdRecommendationGet({
    headers: { authorization: `Bearer ${token}` },
    path: { vehicle_id: 'honda-civic-2019-lx' },
  })
  if (!('data' in response) || !response.data) throw new Error('Recommendation unavailable')
  return response.data
}
