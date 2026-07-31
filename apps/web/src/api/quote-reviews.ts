import type { QuoteDecisionResponse, QuoteReviewResponse } from './generated/types.gen'
import {
  decideQuoteReviewQuoteReviewsReviewIdDecisionPost,
  openQuoteReviewVehiclesVehicleIdQuoteReviewsPost,
} from './generated/sdk.gen'
import type { AdvisorContext } from './advisor-context'
import { traceHeaders } from './advisor-context'

export async function openQuoteReview(
  token: string,
  serviceCodes: string[],
  context: AdvisorContext,
): Promise<QuoteReviewResponse> {
  const response = await openQuoteReviewVehiclesVehicleIdQuoteReviewsPost({
    body: { service_codes: serviceCodes },
    headers: { authorization: `Bearer ${token}`, ...traceHeaders(context) },
    path: { vehicle_id: context.vehicleId },
  })
  if (!('data' in response) || !response.data) throw new Error('Quote review unavailable')
  return response.data
}

export async function decideQuoteReview(
  token: string,
  reviewId: string,
  decision: 'approve' | 'reject',
  options: { idempotencyKey: string; reason?: string; context: AdvisorContext },
): Promise<QuoteDecisionResponse> {
  const response = await decideQuoteReviewQuoteReviewsReviewIdDecisionPost({
    body: { decision, idempotency_key: options.idempotencyKey, reason: options.reason ?? null },
    headers: { authorization: `Bearer ${token}`, ...traceHeaders(options.context) },
    path: { review_id: reviewId },
  })
  if (!('data' in response) || !response.data) throw new Error('Quote decision was not saved')
  return response.data
}
