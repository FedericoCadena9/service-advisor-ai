import { useState } from "react";

import { Button } from "@/components/ui/button";
import { failureMessage } from "../../api/failure";
import type {
  QuoteDecisionResponse,
  QuoteReviewResponse,
} from "../../api/generated/types.gen";

const APPROVAL_BUNDLE = ["HONDA-A1"];

export function QuoteApprovalPanel({
  onOpenReview,
  onDecide,
  onApproved,
}: {
  onOpenReview: (serviceCodes: string[]) => Promise<QuoteReviewResponse>;
  onDecide: (
    reviewId: string,
    decision: "approve" | "reject",
    reason?: string,
  ) => Promise<QuoteDecisionResponse>;
  onApproved: (quoteId: string) => void;
}) {
  const [review, setReview] = useState<QuoteReviewResponse>();
  const [decision, setDecision] = useState<QuoteDecisionResponse>();
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");

  async function openReview() {
    setDecision(undefined);
    setError("");
    try {
      setReview(await onOpenReview(APPROVAL_BUNDLE));
    } catch (failure) {
      setReview(undefined);
      setError(
        failureMessage(failure, "The quote could not be opened for approval"),
      );
    }
  }

  /**
   * The decision endpoint is the one place a 409 is ambiguous: it answers the same status
   * for a lost check-in and for a quote invalidated by changed inputs. Opening the review
   * is what proves the check-in is still there, and these buttons only exist once it
   * succeeded, so a 409 here is read as the invalidation it almost always is.
   */
  async function decide(choice: "approve" | "reject") {
    if (!review) return;
    try {
      const saved = await onDecide(
        review.id,
        choice,
        choice === "reject" ? "Customer declined" : reason || undefined,
      );
      setDecision(saved);
      if (saved.quote_id) onApproved(saved.quote_id);
      setError("");
    } catch {
      setDecision(undefined);
      setError(
        "Quote returned to review: inputs changed or a Manager decision is required",
      );
    }
  }

  return (
    <div className="space-y-3">
      <p className="text-sm text-muted-foreground">
        The approval command is the boundary between a priced proposal and
        customer-facing work.
      </p>
      <Button onClick={() => void openReview()}>Open approval</Button>
      {review && (
        <dl className="grid gap-3 rounded-lg border border-border bg-muted/40 p-4 text-sm sm:grid-cols-2 [&_dt]:text-xs [&_dt]:uppercase [&_dt]:tracking-wide [&_dt]:text-muted-foreground [&_dd]:mt-1 [&_dd]:font-medium">
          <dt>Approver</dt>
          <dd>{`${review.approver_role} · session ${review.approver_session_id}`}</dd>
          <dt>Selected services</dt>
          <dd>{review.facts.service_codes.join(", ")}</dd>
          <dt>Structured facts</dt>
          <dd>{`${review.facts.total_mxn} MXN including IVA ${review.facts.iva_mxn} · ${review.facts.duration_minutes} min · ${review.facts.bay_slot_id ?? "no bay slot"}`}</dd>
          <dt>Citations</dt>
          <dd>{`${review.citations.rule_version} · page ${review.citations.citation_page}, ${review.citations.citation_section}`}</dd>
        </dl>
      )}
      {review?.evidence_blocked && (
        <p
          role="alert"
          className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive"
        >{`Not approvable by any role: ${review.blocking_reason}`}</p>
      )}
      {review?.escalation_required && !review.evidence_blocked && (
        <div className="mt-3">
          <p className="rounded-lg border border-amber-300/20 bg-amber-300/5 p-3 text-sm text-amber-100">{`Manager review required: ${review.escalation_reasons.join("; ")}`}</p>
          <label
            className="mb-1.5 block text-sm font-medium"
            htmlFor="escalation-reason"
          >
            Manager reason
          </label>
          <input
            id="escalation-reason"
            value={reason}
            onChange={(event) => setReason(event.target.value)}
          />
        </div>
      )}
      {review && !review.evidence_blocked && (
        <div className="flex flex-wrap gap-2">
          <Button onClick={() => void decide("approve")}>Approve quote</Button>
          <Button variant="outline" onClick={() => void decide("reject")}>
            Reject quote
          </Button>
        </div>
      )}
      {decision && (
        <p
          role="status"
          className="rounded-lg border border-emerald-400/35 bg-emerald-50 p-3 text-sm text-emerald-800"
        >
          {decision.decision === "approved"
            ? `Quote ${decision.quote_id} approved by ${decision.approver_role}`
            : `Quote rejected by ${decision.approver_role}: ${decision.reason}`}
        </p>
      )}
      {error && (
        <p
          role="alert"
          className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive"
        >
          {error}
        </p>
      )}
    </div>
  );
}
