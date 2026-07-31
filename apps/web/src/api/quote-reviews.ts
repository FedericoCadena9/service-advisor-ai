import type { QuoteDecisionResponse, QuoteReviewResponse } from './generated/types.gen'
import {
  decideQuoteReviewQuoteReviewsReviewIdDecisionPost,
  openQuoteReviewVehiclesVehicleIdQuoteReviewsPost,
} from './generated/sdk.gen'

export async function openQuoteReview(token: string, serviceCodes: string[]): Promise<QuoteReviewResponse> {
  const response = await openQuoteReviewVehiclesVehicleIdQuoteReviewsPost({
    body: { service_codes: serviceCodes },
    headers: { authorization: `Bearer ${token}` },
    path: { vehicle_id: 'honda-civic-2019-lx' },
  })
  if (!('data' in response) || !response.data) throw new Error('Quote review unavailable')
  return response.data
}

export async function decideQuoteReview(
  token: string,
  reviewId: string,
  decision: 'approve' | 'reject',
  options: { idempotencyKey: string; reason?: string },
): Promise<QuoteDecisionResponse> {
  const response = await decideQuoteReviewQuoteReviewsReviewIdDecisionPost({
    body: { decision, idempotency_key: options.idempotencyKey, reason: options.reason ?? null },
    headers: { authorization: `Bearer ${token}` },
    path: { review_id: reviewId },
  })
  if (!('data' in response) || !response.data) throw new Error('Quote decision was not saved')
  return response.data
}
