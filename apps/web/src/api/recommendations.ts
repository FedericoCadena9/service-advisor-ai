import type { RecommendationResponse } from './generated/types.gen'
import { getRecommendationVehiclesVehicleIdRecommendationGet } from './generated/sdk.gen'
import type { AdvisorContext } from './advisor-context'
import { traceHeaders } from './advisor-context'

export async function fetchRecommendation(
  token: string,
  context: AdvisorContext,
): Promise<RecommendationResponse> {
  const response = await getRecommendationVehiclesVehicleIdRecommendationGet({
    headers: { authorization: `Bearer ${token}`, ...traceHeaders(context) },
    path: { vehicle_id: context.vehicleId },
  })
  if (!('data' in response) || !response.data) throw new Error('Recommendation unavailable')
  return response.data
}
