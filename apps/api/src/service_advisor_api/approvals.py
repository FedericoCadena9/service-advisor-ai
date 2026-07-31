from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from threading import RLock
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
# A quote snapshot is only trustworthy while its volatile inputs are still fresh.
QUOTE_VALIDITY = timedelta(hours=24)


class StaleQuoteError(RuntimeError):
    """Raised when a quote can no longer be trusted: changed inputs, expiry, or invalidation."""


class AlreadyDecidedError(RuntimeError):
    """Raised when a decided quote is decided again in the opposite direction."""


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
    expires_at: str
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
        self._lock = RLock()
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
        now: datetime | None = None,
    ) -> QuoteReview:
        expires_at = _as_utc(now or datetime.now(UTC)) + QUOTE_VALIDITY
        review = QuoteReview(
            id=str(uuid4()),
            shop_id=shop_id,
            demo_session_id=demo_session_id,
            vehicle_id=vehicle_id,
            facts=facts,
            citations=citations,
            fingerprint=fingerprint,
            expires_at=expires_at.isoformat(),
        )
        with self._lock:
            self._reviews[review.id] = review
        return review

    def get(self, review_id: str, *, shop_id: str, demo_session_id: str) -> QuoteReview:
        with self._lock:
            review = self._reviews[review_id]
        if (review.shop_id, review.demo_session_id) != (shop_id, demo_session_id):
            raise PermissionError("Quote review is outside this demo session")
        return review

    def revalidate(
        self, review_id: str, current_facts: QuoteFacts, current_fingerprint: str
    ) -> QuoteReview:
        with self._lock:
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
        now: datetime | None = None,
    ) -> QuoteDecision:
        with self._lock:
            review = self.get(review_id, shop_id=shop_id, demo_session_id=demo_session_id)
            if review.status == "rejected":
                raise StaleQuoteError("Quote was rejected and must be redrafted")
            if _has_expired(review, now):
                raise StaleQuoteError("The quote expired and must be redrafted")
            if current_fingerprint != review.fingerprint:
                self._invalidate(review, current_facts, current_fingerprint)
                raise StaleQuoteError(
                    "Price, inventory, or slot inputs changed; the quote returned to review"
                )
            authorize_decision(escalation, approver_role)
            if escalation.required and not (reason or "").strip():
                raise EscalationReasonRequiredError(
                    "An escalated quote requires a recorded reason"
                )

            replayed = self._idempotency.get((review_id, idempotency_key))
            existing = self._decision_for(review_id)
            if replayed is not None and existing is not None and existing.id == replayed:
                return existing
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
        with self._lock:
            review = self.get(review_id, shop_id=shop_id, demo_session_id=demo_session_id)
            existing = self._decision_for(review_id)
            if (
                existing is not None
                and existing.decision == "approved"
                and review.status == "approved"
            ):
                raise AlreadyDecidedError(
                    "The quote is already approved; invalidate or redraft it before rejecting"
                )
            if existing is not None and existing.decision == "rejected":
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

    def approved_quote(
        self, quote_id: str, *, shop_id: str, demo_session_id: str, now: datetime | None = None
    ) -> tuple[QuoteDecision, QuoteReview]:
        """An approval only stays usable while its review is still approved and unexpired."""
        with self._lock:
            decision = next(
                (
                    entry
                    for entry in self._audit
                    if entry.quote_id == quote_id and entry.decision == "approved"
                ),
                None,
            )
            if decision is None:
                raise KeyError(quote_id)
            review = self.get(
                decision.review_id, shop_id=shop_id, demo_session_id=demo_session_id
            )
        if review.status != "approved" or review.fingerprint != decision.fingerprint:
            raise StaleQuoteError(
                "The approval was invalidated; the quote returned to review"
            )
        if _has_expired(review, now):
            raise StaleQuoteError("The approved quote expired")
        return decision, review

    def audit_trail(self, shop_id: str) -> tuple[QuoteDecision, ...]:
        with self._lock:
            return tuple(
                decision for decision in self._audit if self._shop_of(decision) == shop_id
            )

    def _decision_for(self, review_id: str) -> QuoteDecision | None:
        return self._decisions.get(review_id)

    def _record(self, decision: QuoteDecision) -> None:
        self._decisions[decision.review_id] = decision
        self._audit.append(decision)

    def _invalidate(
        self, review: QuoteReview, current_facts: QuoteFacts, current_fingerprint: str
    ) -> None:
        if review.status == "rejected":
            # A rejection is final: changed inputs require a fresh draft, not a reopening.
            return
        self._reviews[review.id] = replace(
            review,
            facts=current_facts,
            fingerprint=current_fingerprint,
            status="in_review",
            invalidation_reason="Volatile pricing, inventory, or slot inputs changed",
        )

    def _shop_of(self, decision: QuoteDecision) -> str:
        return self._reviews[decision.review_id].shop_id


def _as_utc(moment: datetime) -> datetime:
    """A naive clock is read as UTC so an expiry comparison can never raise."""
    return moment.replace(tzinfo=UTC) if moment.tzinfo is None else moment


def _has_expired(review: QuoteReview, now: datetime | None) -> bool:
    return _as_utc(now or datetime.now(UTC)) >= _as_utc(
        datetime.fromisoformat(review.expires_at)
    )
