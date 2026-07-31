from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

ESCALATION_THRESHOLD_MXN = Decimal("15000.00")
REPEATED_DECLINE_THRESHOLD = 2


class EvidenceInsufficientError(RuntimeError):
    """Raised when evidence is missing or contradictory; no role may override this."""


class EscalationRequiredError(PermissionError):
    """Raised when an Advisor tries to complete a quote command reserved for a Manager."""


class EscalationReasonRequiredError(ValueError):
    """Raised when a Manager decides an escalated quote without recording a reason."""


@dataclass(frozen=True)
class EscalationAssessment:
    required: bool
    reasons: tuple[str, ...]
    evidence_blocked: bool
    blocking_reason: str | None


def assess_escalation(
    *,
    total_mxn: Decimal,
    rule_version: str | None,
    citation_page: int | None,
    declines_per_service: Sequence[int] = (),
    invalidation_reason: str | None = None,
    unavailable_service_codes: Sequence[str] = (),
) -> EscalationAssessment:
    """Identify the agreed escalation conditions before any quote command can complete."""
    if rule_version is None or citation_page is None:
        return EscalationAssessment(
            required=True,
            reasons=("Reviewed evidence is missing or contradictory",),
            evidence_blocked=True,
            blocking_reason="Reviewed evidence is missing or contradictory",
        )

    reasons: list[str] = []
    if total_mxn > ESCALATION_THRESHOLD_MXN:
        reasons.append(f"Quote total exceeds MXN {ESCALATION_THRESHOLD_MXN:,.2f}")
    if any(count >= REPEATED_DECLINE_THRESHOLD for count in declines_per_service):
        reasons.append("Customer repeatedly declined a quoted service")
    if invalidation_reason is not None:
        reasons.append(f"Operational inputs changed: {invalidation_reason}")
    if unavailable_service_codes:
        reasons.append(
            f"Unavailable operations exception: {', '.join(sorted(unavailable_service_codes))}"
        )
    return EscalationAssessment(
        required=bool(reasons),
        reasons=tuple(reasons),
        evidence_blocked=False,
        blocking_reason=None,
    )


def authorize_decision(assessment: EscalationAssessment, approver_role: str) -> None:
    """Gate a quote command on evidence sufficiency and Manager authority."""
    if assessment.evidence_blocked:
        raise EvidenceInsufficientError(assessment.blocking_reason or "Evidence is insufficient")
    if assessment.required and approver_role not in ("manager", "admin"):
        raise EscalationRequiredError("A Manager must decide this escalated quote")
