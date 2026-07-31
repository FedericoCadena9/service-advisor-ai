import { expect, test, vi } from 'vitest'

import { traceHeaders } from './advisor-context'
import { askContextualChat } from './chat'
import { fetchRecommendation } from './recommendations'
import { contextualChatContextualChatPost } from './generated/sdk.gen'
import { getRecommendationVehiclesVehicleIdRecommendationGet } from './generated/sdk.gen'

vi.mock('./generated/sdk.gen', () => ({
  contextualChatContextualChatPost: vi.fn().mockResolvedValue({ data: { text: 'ok' } }),
  getRecommendationVehiclesVehicleIdRecommendationGet: vi
    .fn()
    .mockResolvedValue({ data: { state: 'due_now' } }),
}))

const CONTEXT = { vehicleId: 'toyota-corolla-2022-le', currentMileageKm: 40_000, traceId: 'trace-1' }

test('a run correlates its calls with the trace header', () => {
  expect(traceHeaders({ traceId: 'trace-1' })).toEqual({ 'x-trace-id': 'trace-1' })
})

test('what if there is no run yet instead of an active one — no header is invented', () => {
  expect(traceHeaders({ traceId: null })).toEqual({})
})

test('chat asks about the vehicle on screen, not a hardcoded Civic', async () => {
  await askContextualChat('token', 'Why is this due?', CONTEXT)

  expect(vi.mocked(contextualChatContextualChatPost)).toHaveBeenCalledWith(
    expect.objectContaining({
      body: expect.objectContaining({
        vehicle_id: 'toyota-corolla-2022-le',
        current_mileage_km: 40_000,
      }),
      headers: expect.objectContaining({ 'x-trace-id': 'trace-1' }),
    }),
  )
})

test('recommendation reads the selected vehicle and carries the run trace', async () => {
  await fetchRecommendation('token', CONTEXT)

  expect(vi.mocked(getRecommendationVehiclesVehicleIdRecommendationGet)).toHaveBeenCalledWith(
    expect.objectContaining({
      path: { vehicle_id: 'toyota-corolla-2022-le' },
      headers: expect.objectContaining({ 'x-trace-id': 'trace-1' }),
    }),
  )
})
