import type { ExplanationResponse } from './generated/types.gen'
import { contextualChatContextualChatPost } from './generated/sdk.gen'
import type { AdvisorContext } from './advisor-context'
import { traceHeaders } from './advisor-context'

export async function askContextualChat(
  token: string,
  question: string,
  context: AdvisorContext,
): Promise<ExplanationResponse> {
  const response = await contextualChatContextualChatPost({
    body: {
      question,
      vehicle_id: context.vehicleId,
      current_mileage_km: context.currentMileageKm,
      provider_available: true,
    },
    headers: { authorization: `Bearer ${token}`, ...traceHeaders(context) },
  })
  if (!('data' in response) || !response.data) throw new Error('Contextual chat unavailable')
  return response.data
}
