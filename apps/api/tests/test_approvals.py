from decimal import Decimal

import pytest

from service_advisor_api.approvals import (
    APPLICATION_COMMANDS,
    LLM_TOOL_ALLOWLIST,
    QuoteCitations,
    QuoteCommandStore,
    QuoteFacts,
    StaleQuoteError,
)
from service_advisor_api.escalation import EscalationAssessment

FACTS = QuoteFacts(
    service_codes=("HONDA-A1",),
    subtotal_mxn=Decimal("1593.00"),
    iva_mxn=Decimal("254.88"),
    total_mxn=Decimal("1847.88"),
    duration_minutes=50,
    bay_slot_id="bay-1-morning",
)
REPRICED_FACTS = QuoteFacts(**{**FACTS.__dict__, "total_mxn": Decimal("1999.00")})
CITATIONS = QuoteCitations("honda-civic-2019-lx-v1", 42, "Maintenance Minder")


def _open_review(store: QuoteCommandStore):
    return store.open_review(
        shop_id="demo-shop",
        demo_session_id="session-1",
        vehicle_id="honda-civic-2019-lx",
        facts=FACTS,
        citations=CITATIONS,
        fingerprint="fingerprint-a",
    )


NO_ESCALATION = EscalationAssessment(
    required=False, reasons=(), evidence_blocked=False, blocking_reason=None
)


def _approve(
    store: QuoteCommandStore,
    review_id: str,
    *,
    key: str,
    fingerprint: str,
    role: str = "advisor",
    escalation: EscalationAssessment = NO_ESCALATION,
    reason: str | None = None,
):
    return store.approve(
        review_id,
        shop_id="demo-shop",
        demo_session_id="session-1",
        approver_role=role,
        approver_session_id="session-1",
        idempotency_key=key,
        current_facts=FACTS,
        current_fingerprint=fingerprint,
        escalation=escalation,
        reason=reason,
    )


def test_approval_records_the_authenticated_approver_facts_and_citations():
    store = QuoteCommandStore()
    review = _open_review(store)

    decision = _approve(store, review.id, key="key-1", fingerprint="fingerprint-a")

    assert decision.decision == "approved"
    assert decision.approver_role == "advisor"
    assert decision.approver_session_id == "session-1"
    assert decision.facts == FACTS
    assert decision.citations == CITATIONS


def test_repeated_approval_saves_at_most_one_quote():
    store = QuoteCommandStore()
    review = _open_review(store)

    first = _approve(store, review.id, key="key-1", fingerprint="fingerprint-a")
    repeat = _approve(store, review.id, key="key-1", fingerprint="fingerprint-a")
    other_key = _approve(store, review.id, key="key-2", fingerprint="fingerprint-a")

    assert first.quote_id == repeat.quote_id == other_key.quote_id
    assert len(store.audit_trail("demo-shop")) == 1


def test_changed_volatile_inputs_block_approval_and_return_the_quote_to_review():
    store = QuoteCommandStore()
    review = _open_review(store)

    with pytest.raises(StaleQuoteError):
        _approve(store, review.id, key="key-1", fingerprint="fingerprint-b")

    reloaded = store.get(review.id, "demo-shop", "session-1")
    assert reloaded.status == "in_review"
    assert reloaded.invalidation_reason == "Volatile pricing, inventory, or slot inputs changed"
    assert store.audit_trail("demo-shop") == ()


def test_revalidation_invalidates_a_prior_approval():
    store = QuoteCommandStore()
    review = _open_review(store)
    _approve(store, review.id, key="key-1", fingerprint="fingerprint-a")

    revalidated = store.revalidate(review.id, REPRICED_FACTS, "fingerprint-b")

    assert revalidated.status == "in_review"
    assert revalidated.facts.total_mxn == Decimal("1999.00")


def test_rejection_is_attributed_and_blocks_later_approval():
    store = QuoteCommandStore()
    review = _open_review(store)

    rejected = store.reject(
        review.id,
        shop_id="demo-shop",
        demo_session_id="session-1",
        approver_role="advisor",
        approver_session_id="session-1",
        reason="Customer declined the bundle",
    )

    assert rejected.quote_id is None
    assert rejected.reason == "Customer declined the bundle"
    with pytest.raises(StaleQuoteError):
        _approve(store, review.id, key="key-1", fingerprint="fingerprint-a")


def test_reviews_outside_the_demo_session_are_not_readable():
    store = QuoteCommandStore()
    review = _open_review(store)

    with pytest.raises(PermissionError):
        store.get(review.id, "demo-shop", "session-2")


def test_quote_writes_are_commands_and_never_model_tools():
    assert set(LLM_TOOL_ALLOWLIST).isdisjoint(APPLICATION_COMMANDS)
    assert all(tool.startswith("read_") for tool in LLM_TOOL_ALLOWLIST)
