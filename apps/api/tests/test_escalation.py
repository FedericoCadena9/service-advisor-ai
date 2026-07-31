from decimal import Decimal

import pytest

from service_advisor_api.escalation import (
    EscalationRequiredError,
    EvidenceInsufficientError,
    assess_escalation,
    authorize_decision,
)

GROUNDED = {"rule_version": "honda-civic-2019-lx-v1", "citation_page": 42}


def test_standard_quote_needs_no_escalation():
    assessment = assess_escalation(total_mxn=Decimal("1847.88"), **GROUNDED)

    assert assessment.required is False
    assert assessment.reasons == ()


def test_total_above_the_agreed_threshold_escalates():
    assessment = assess_escalation(total_mxn=Decimal("15000.01"), **GROUNDED)

    assert assessment.required is True
    assert assessment.reasons == ("Quote total exceeds MXN 15,000.00",)


def test_threshold_is_inclusive_of_the_agreed_limit():
    assert assess_escalation(total_mxn=Decimal("15000.00"), **GROUNDED).required is False


def test_repeated_declines_escalate():
    assessment = assess_escalation(
        total_mxn=Decimal("1000.00"), declines_per_service=(2,), **GROUNDED
    )

    assert assessment.reasons == ("Customer repeatedly declined a quoted service",)


def test_changed_operational_inputs_escalate():
    assessment = assess_escalation(
        total_mxn=Decimal("1000.00"),
        invalidation_reason="Volatile pricing, inventory, or slot inputs changed",
        **GROUNDED,
    )

    assert assessment.reasons == (
        "Operational inputs changed: Volatile pricing, inventory, or slot inputs changed",
    )


def test_unavailable_operations_escalate_as_an_exception():
    assessment = assess_escalation(
        total_mxn=Decimal("1000.00"),
        unavailable_service_codes=("HONDA-CABIN-FILTER",),
        **GROUNDED,
    )

    assert assessment.reasons == (
        "Unavailable operations exception: HONDA-CABIN-FILTER",
    )


def test_missing_evidence_blocks_every_role():
    assessment = assess_escalation(
        total_mxn=Decimal("1000.00"), rule_version=None, citation_page=None
    )

    assert assessment.evidence_blocked is True
    for role in ("advisor", "manager", "admin"):
        with pytest.raises(EvidenceInsufficientError):
            authorize_decision(assessment, role)


def test_advisors_cannot_decide_an_escalated_quote():
    assessment = assess_escalation(total_mxn=Decimal("20000.00"), **GROUNDED)

    with pytest.raises(EscalationRequiredError):
        authorize_decision(assessment, "advisor")
    authorize_decision(assessment, "manager")
    authorize_decision(assessment, "admin")
