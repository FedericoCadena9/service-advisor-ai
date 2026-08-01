import type { CheckinRequest, CheckinResponse } from './generated/types.gen'
import { createCheckinVehiclesVehicleIdCheckInsPost } from './generated/sdk.gen'
import { requestFailed } from './failure'

export async function saveCheckin(
  token: string,
  checkin: CheckinRequest,
): Promise<CheckinResponse> {
  const response = await createCheckinVehiclesVehicleIdCheckInsPost({
    body: checkin,
    headers: { authorization: `Bearer ${token}` },
    path: { vehicle_id: 'honda-civic-2019-lx' },
  })

  if (!('data' in response) || !response.data) {
    throw requestFailed('Check-in could not be saved', response)
  }

  return response.data
}
