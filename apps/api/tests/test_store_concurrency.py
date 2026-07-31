from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest

from service_advisor_api.appointments import AppointmentStore
from service_advisor_api.approvals import QuoteCitations, QuoteCommandStore, QuoteFacts
from service_advisor_api.escalation import EscalationAssessment
from service_advisor_api.messaging import MessagingStore
from service_advisor_api.voice import VoiceNoteStore, transcribe

FACTS = QuoteFacts(
    service_codes=("HONDA-A1",),
    subtotal_mxn=Decimal("1593.00"),
    iva_mxn=Decimal("254.88"),
    total_mxn=Decimal("1847.88"),
    duration_minutes=50,
    bay_slot_id="bay-1-morning",
)
CITATIONS = QuoteCitations("honda-civic-2019-lx-v1", 42, "Maintenance Minder")
NO_ESCALATION = EscalationAssessment(
    required=False, reasons=(), evidence_blocked=False, blocking_reason=None
)


def test_concurrent_approvals_still_save_one_quote() -> None:
    """What if two advisors approve the same review at the same instant, not one after another?"""
    store = QuoteCommandStore()
    review = store.open_review(
        shop_id="demo-shop",
        demo_session_id="session-1",
        vehicle_id="honda-civic-2019-lx",
        facts=FACTS,
        citations=CITATIONS,
        fingerprint="fingerprint-a",
    )

    def approve(key: str):
        return store.approve(
            review.id,
            shop_id="demo-shop",
            demo_session_id="session-1",
            approver_role="advisor",
            approver_session_id="session-1",
            idempotency_key=key,
            current_facts=FACTS,
            current_fingerprint="fingerprint-a",
            escalation=NO_ESCALATION,
        )

    with ThreadPoolExecutor(max_workers=8) as pool:
        decisions = list(pool.map(approve, [f"key-{index}" for index in range(8)]))

    assert len({decision.quote_id for decision in decisions}) == 1
    assert len(store.audit_trail("demo-shop")) == 1


def test_concurrent_enqueue_delivers_one_message() -> None:
    """What if the Advisor double-clicks enqueue instead of sending once?"""
    store = MessagingStore()

    def enqueue(_: int):
        return store.enqueue(
            quote_id="quote-1",
            shop_id="demo-shop",
            demo_session_id="session-1",
            text="Hola Demo Customer: ¿Confirma la cita?",
            segments=1,
            approver_role="advisor",
            rule_version="honda-civic-2019-lx-v1",
            citation_page=42,
            citation_section="Maintenance Minder",
        )

    with ThreadPoolExecutor(max_workers=8) as pool:
        deliveries = list(pool.map(enqueue, range(8)))

    assert len({delivery.id for delivery in deliveries}) == 1
    assert store.get(deliveries[0].id, shop_id="demo-shop", demo_session_id="session-1").state == "queued"


def test_concurrent_reservations_hold_one_slot() -> None:
    """What if the reserve request is retried in parallel instead of sequentially?"""
    store = AppointmentStore()

    def reserve(_: int):
        return store.reserve(
            quote_id="quote-1",
            shop_id="demo-shop",
            demo_session_id="session-1",
            bay_slot_id="bay-1-morning",
            starts_at="2026-08-03T09:00:00",
            approver_role="advisor",
        )

    with ThreadPoolExecutor(max_workers=8) as pool:
        appointments = list(pool.map(reserve, range(8)))

    assert len({appointment.id for appointment in appointments}) == 1


def test_concurrent_voice_saves_keep_every_note_readable() -> None:
    """What if several Advisors record at once instead of one at a time?"""
    store = VoiceNoteStore()

    def save(index: int):
        return store.save(
            transcribe(
                shop_id="demo-shop",
                demo_session_id=f"session-{index}",
                language="es",
                duration_seconds=30.0,
                consent=True,
                provider_available=True,
            )
        )

    with ThreadPoolExecutor(max_workers=8) as pool:
        notes = list(pool.map(save, range(8)))

    for index, note in enumerate(notes):
        assert store.get(note.id, shop_id="demo-shop", demo_session_id=f"session-{index}").id == note.id


@pytest.mark.parametrize(
    ("store_call", "swapped"),
    [
        ("quote_review", True),
        ("voice_note", True),
        ("appointment", True),
        ("message", True),
    ],
)
def test_tenancy_arguments_cannot_be_passed_positionally(store_call: str, swapped: bool) -> None:
    """What if a caller swaps shop_id and demo_session_id instead of ordering them right?"""
    del swapped
    stores = {
        "quote_review": (QuoteCommandStore().get, ("review-1", "demo-shop", "session-1")),
        "voice_note": (VoiceNoteStore().get, ("note-1", "demo-shop", "session-1")),
        "appointment": (AppointmentStore().for_quote, ("quote-1", "demo-shop", "session-1")),
        "message": (MessagingStore().get, ("delivery-1", "demo-shop", "session-1")),
    }
    call, arguments = stores[store_call]

    with pytest.raises(TypeError):
        call(*arguments)
