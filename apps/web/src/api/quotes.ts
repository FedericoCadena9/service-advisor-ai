import type { QuoteDraftResponse } from './generated/types.gen'
import { createQuoteDraftVehiclesVehicleIdQuoteDraftsPost } from './generated/sdk.gen'

export async function draftQuote(token: string, serviceCodes: string[]): Promise<QuoteDraftResponse> {
  const response = await createQuoteDraftVehiclesVehicleIdQuoteDraftsPost({
    body: { service_codes: serviceCodes },
    headers: { authorization: `Bearer ${token}` },
    path: { vehicle_id: 'honda-civic-2019-lx' },
  })
  if (!('data' in response) || !response.data) throw new Error('Quote draft unavailable')
  return response.data
}
