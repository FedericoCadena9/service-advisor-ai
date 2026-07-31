import type { ExplanationResponse } from './generated/types.gen'
import { contextualChatContextualChatPost } from './generated/sdk.gen'

export async function askContextualChat(token: string, question: string): Promise<ExplanationResponse> {
  const response = await contextualChatContextualChatPost({ body: { question, current_mileage_km: 48000, provider_available: true }, headers: { authorization: `Bearer ${token}` } })
  if (!('data' in response) || !response.data) throw new Error('Contextual chat unavailable')
  return response.data
}
