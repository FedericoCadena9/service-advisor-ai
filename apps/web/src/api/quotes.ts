import type { QuoteDraftResponse } from './generated/types.gen'
import { createQuoteDraftVehiclesVehicleIdQuoteDraftsPost } from './generated/sdk.gen'
import type { AdvisorContext } from './advisor-context'
import { traceHeaders } from './advisor-context'

export async function draftQuote(
  token: string,
  serviceCodes: string[],
  context: AdvisorContext,
): Promise<QuoteDraftResponse> {
  const response = await createQuoteDraftVehiclesVehicleIdQuoteDraftsPost({
    body: { service_codes: serviceCodes },
    headers: { authorization: `Bearer ${token}`, ...traceHeaders(context) },
    path: { vehicle_id: context.vehicleId },
  })
  if (!('data' in response) || !response.data) throw new Error('Quote draft unavailable')
  return response.data
}
