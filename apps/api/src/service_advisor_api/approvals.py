from dataclasses import dataclass, replace
from decimal import Decimal
from uuid import uuid4

from service_advisor_api.escalation import (
    EscalationAssessment,
    EscalationReasonRequiredError,
    authorize_decision,
)

# Read-only retrieval the language model may call. Saving a quote is an application
# command, never a model tool, so these registries must stay disjoint.
LLM_TOOL_ALLOWLIST = (
    "read_recommendation",
    "read_service_history",
    "read_quote_draft",
)
APPLICATION_COMMANDS = (
    "approve_quote",
    "reject_quote",
)


class StaleQuoteError(RuntimeError):
    """Raised when volatile pricing, inventory, or slot inputs changed since review."""


@dataclass(frozen=True)
class QuoteFacts:
    service_codes: tuple[str, ...]
    subtotal_mxn: Decimal
    iva_mxn: Decimal
    total_mxn: Decimal
    duration_minutes: int
    bay_slot_id: str | None


@dataclass(frozen=True)
class QuoteCitations:
    rule_version: str | None
    citation_page: int | None
    citation_section: str | None


@dataclass(frozen=True)
class QuoteReview:
    id: str
    shop_id: str
    demo_session_id: str
    vehicle_id: str
    facts: QuoteFacts
    citations: QuoteCitations
    fingerprint: str
    status: str = "in_review"
    invalidation_reason: str | None = None


@dataclass(frozen=True)
class QuoteDecision:
    id: str
    review_id: str
    quote_id: str | None
    decision: str
    approver_role: str
    approver_session_id: str
    reason: str | None
    facts: QuoteFacts
    citations: QuoteCitations
    fingerprint: str
    escalation_reasons: tuple[str, ...] = ()


class QuoteCommandStore:
    """The single write path for quote decisions, with an append-only audit trail."""

    def __init__(self) -> None:
        self._reviews: dict[str, QuoteReview] = {}
        self._decisions: dict[str, QuoteDecision] = {}
        self._audit: list[QuoteDecision] = []
        self._idempotency: dict[tuple[str, str], str] = {}

    def open_review(
        self,
        *,
        shop_id: str,
        demo_session_id: str,
        vehicle_id: str,
        facts: QuoteFacts,
        citations: QuoteCitations,
        fingerprint: str,
    ) -> QuoteReview:
        review = QuoteReview(
            id=str(uuid4()),
            shop_id=shop_id,
            demo_session_id=demo_session_id,
            vehicle_id=vehicle_id,
            facts=facts,
            citations=citations,
            fingerprint=fingerprint,
        )
        self._reviews[review.id] = review
        return review

    def get(self, review_id: str, shop_id: str, demo_session_id: str) -> QuoteReview:
        review = self._reviews[review_id]
        if (review.shop_id, review.demo_session_id) != (shop_id, demo_session_id):
            raise PermissionError("Quote review is outside this demo session")
        return review

    def revalidate(
        self, review_id: str, current_facts: QuoteFacts, current_fingerprint: str
    ) -> QuoteReview:
        review = self._reviews[review_id]
        if current_fingerprint == review.fingerprint:
            return review
        self._invalidate(review, current_facts, current_fingerprint)
        return self._reviews[review_id]

    def approve(
        self,
        review_id: str,
        *,
        shop_id: str,
        demo_session_id: str,
        approver_role: str,
        approver_session_id: str,
        idempotency_key: str,
        current_facts: QuoteFacts,
        current_fingerprint: str,
        escalation: EscalationAssessment,
        reason: str | None = None,
    ) -> QuoteDecision:
        review = self.get(review_id, shop_id, demo_session_id)
        if review.status == "rejected":
            raise StaleQuoteError("Quote was rejected and must be redrafted")
        if current_fingerprint != review.fingerprint:
            self._invalidate(review, current_facts, current_fingerprint)
            raise StaleQuoteError(
                "Price, inventory, or slot inputs changed; the quote returned to review"
            )
        authorize_decision(escalation, approver_role)
        if escalation.required and not (reason or "").strip():
            raise EscalationReasonRequiredError("An escalated quote requires a recorded reason")

        existing = self._decision_for(review_id)
        if existing is not None and existing.fingerprint == review.fingerprint:
            self._idempotency[(review_id, idempotency_key)] = existing.id
            return existing

        decision = QuoteDecision(
            id=str(uuid4()),
            review_id=review_id,
            quote_id=str(uuid4()),
            decision="approved",
            approver_role=approver_role,
            approver_session_id=approver_session_id,
            reason=reason,
            facts=review.facts,
            citations=review.citations,
            fingerprint=review.fingerprint,
            escalation_reasons=escalation.reasons,
        )
        self._record(decision)
        self._idempotency[(review_id, idempotency_key)] = decision.id
        self._reviews[review_id] = replace(review, status="approved")
        return decision

    def reject(
        self,
        review_id: str,
        *,
        shop_id: str,
        demo_session_id: str,
        approver_role: str,
        approver_session_id: str,
        reason: str,
        escalation_reasons: tuple[str, ...] = (),
    ) -> QuoteDecision:
        review = self.get(review_id, shop_id, demo_session_id)
        existing = self._decision_for(review_id)
        if existing is not None:
            return existing
        decision = QuoteDecision(
            id=str(uuid4()),
            review_id=review_id,
            quote_id=None,
            decision="rejected",
            approver_role=approver_role,
            approver_session_id=approver_session_id,
            reason=reason,
            facts=review.facts,
            citations=review.citations,
            fingerprint=review.fingerprint,
            escalation_reasons=escalation_reasons,
        )
        self._record(decision)
        self._reviews[review_id] = replace(review, status="rejected")
        return decision

    def audit_trail(self, shop_id: str) -> tuple[QuoteDecision, ...]:
        return tuple(decision for decision in self._audit if self._shop_of(decision) == shop_id)

    def _decision_for(self, review_id: str) -> QuoteDecision | None:
        return self._decisions.get(review_id)

    def _record(self, decision: QuoteDecision) -> None:
        self._decisions[decision.review_id] = decision
        self._audit.append(decision)

    def _invalidate(
        self, review: QuoteReview, current_facts: QuoteFacts, current_fingerprint: str
    ) -> None:
        self._reviews[review.id] = replace(
            review,
            facts=current_facts,
            fingerprint=current_fingerprint,
            status="in_review",
            invalidation_reason="Volatile pricing, inventory, or slot inputs changed",
        )

    def _shop_of(self, decision: QuoteDecision) -> str:
        return self._reviews[decision.review_id].shop_id
