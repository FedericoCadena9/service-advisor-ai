import type { HealthResponse } from './generated/types.gen'
import { client } from './generated/client.gen'
import { getHealthHealthGet } from './generated/sdk.gen'

client.setConfig({
  baseUrl: import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000',
})

export async function fetchHealth(): Promise<HealthResponse> {
  const result = await getHealthHealthGet()

  if (!('data' in result) || !result.data) {
    throw new Error('Health request failed')
  }

  return result.data
}
