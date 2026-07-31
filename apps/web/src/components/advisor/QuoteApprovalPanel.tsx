import { useState } from 'react'

import { Button } from '@/components/ui/button'
import type { QuoteDecisionResponse, QuoteReviewResponse } from '../../api/generated/types.gen'

const BUNDLE = ['HONDA-A1']

export function QuoteApprovalPanel({
  onOpenReview,
  onDecide,
  onApproved,
}: {
  onOpenReview: (serviceCodes: string[]) => Promise<QuoteReviewResponse>
  onDecide: (reviewId: string, decision: 'approve' | 'reject', reason?: string) => Promise<QuoteDecisionResponse>
  onApproved: (quoteId: string) => void
}) {
  const [review, setReview] = useState<QuoteReviewResponse>()
  const [decision, setDecision] = useState<QuoteDecisionResponse>()
  const [reason, setReason] = useState('')
  const [error, setError] = useState('')

  async function openReview() {
    setDecision(undefined)
    setError('')
    setReview(await onOpenReview(BUNDLE))
  }

  async function decide(choice: 'approve' | 'reject') {
    if (!review) return
    try {
      const saved = await onDecide(review.id, choice, choice === 'reject' ? 'Customer declined' : reason || undefined)
      setDecision(saved)
      if (saved.quote_id) onApproved(saved.quote_id)
      setError('')
    } catch {
      setDecision(undefined)
      setError('Quote returned to review: inputs changed or a Manager decision is required')
    }
  }

  return (
    <div>
      <Button onClick={() => void openReview()}>Open approval</Button>
      {review && (
        <dl className="mt-3">
          <dt>Approver</dt>
          <dd>{`${review.approver_role} · session ${review.approver_session_id}`}</dd>
          <dt>Selected services</dt>
          <dd>{review.facts.service_codes.join(', ')}</dd>
          <dt>Structured facts</dt>
          <dd>{`${review.facts.total_mxn} MXN including IVA ${review.facts.iva_mxn} · ${review.facts.duration_minutes} min · ${review.facts.bay_slot_id ?? 'no bay slot'}`}</dd>
          <dt>Citations</dt>
          <dd>{`${review.citations.rule_version} · page ${review.citations.citation_page}, ${review.citations.citation_section}`}</dd>
        </dl>
      )}
      {review?.evidence_blocked && <p role="alert">{`Not approvable by any role: ${review.blocking_reason}`}</p>}
      {review?.escalation_required && !review.evidence_blocked && (
        <div className="mt-3">
          <p>{`Manager review required: ${review.escalation_reasons.join('; ')}`}</p>
          <label htmlFor="escalation-reason">Manager reason</label>
          <input
            id="escalation-reason"
            value={reason}
            onChange={(event) => setReason(event.target.value)}
          />
        </div>
      )}
      {review && !review.evidence_blocked && (
        <div className="mt-3">
          <Button onClick={() => void decide('approve')}>Approve quote</Button>
          <Button className="ml-2" onClick={() => void decide('reject')}>
            Reject quote
          </Button>
        </div>
      )}
      {decision && (
        <p role="status">
          {decision.decision === 'approved'
            ? `Quote ${decision.quote_id} approved by ${decision.approver_role}`
            : `Quote rejected by ${decision.approver_role}: ${decision.reason}`}
        </p>
      )}
      {error && <p role="alert">{error}</p>}
    </div>
  )
}
