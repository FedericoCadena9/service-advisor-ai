from decimal import Decimal

import pytest

from service_advisor_api.appointments import AppointmentStore
from service_advisor_api.messaging import (
    InventedContentError,
    MessageTooLongError,
    MessagingStore,
    compose_sms,
    validate_sms,
)

APPROVED = {
    "customer_label": "Demo Customer",
    "service_codes": ("HONDA-A1", "HONDA-TIRE-ROTATION"),
    "total_mxn": Decimal("1847.88"),
    "slot_label": "2026-08-03T09:00:00",
}


def test_preview_is_built_from_approved_fields_only():
    preview = compose_sms(**APPROVED)

    assert "Demo Customer" in preview.text
    assert "$1,847.88 MXN con IVA incluido" in preview.text
    assert "2026-08-03T09:00:00" in preview.text
    assert "¿Confirma la cita?" in preview.text
    assert preview.priorities == ("cambio de aceite y filtro", "rotacion de llantas")


def test_preview_reports_one_to_three_segments():
    preview = compose_sms(**APPROVED)

    assert 1 <= preview.segments <= 3


def test_preview_keeps_at_most_three_priorities():
    preview = compose_sms(
        **{
            **APPROVED,
            "service_codes": (
                "HONDA-A1",
                "HONDA-TIRE-ROTATION",
                "HONDA-CABIN-FILTER",
                "HONDA-BRAKE-PADS-FRONT",
            ),
        }
    )

    assert len(preview.priorities) == 3


def test_edited_text_is_accepted_when_it_stays_grounded():
    edited = (
        "Hola Demo Customer: su servicio incluye cambio de aceite y filtro. "
        "Total $1,847.88 MXN con IVA incluido. Cita 2026-08-03T09:00:00. ¿Confirma la cita?"
    )

    assert validate_sms(edited, **APPROVED) == 1


def test_invented_price_is_rejected():
    edited = compose_sms(**APPROVED).text.replace("1,847.88", "2,500.00")

    with pytest.raises(InventedContentError):
        validate_sms(edited, **APPROVED)


def test_invented_recipient_is_rejected():
    edited = compose_sms(**APPROVED).text.replace("Demo Customer", "Otro Cliente")

    with pytest.raises(InventedContentError):
        validate_sms(edited, **APPROVED)


def test_invented_service_is_rejected():
    edited = compose_sms(**APPROVED).text.replace("Cita", "Incluye HONDA-BRAKE-PADS-FRONT. Cita")

    with pytest.raises(InventedContentError):
        validate_sms(edited, **APPROVED)


def test_invented_slot_is_rejected():
    edited = compose_sms(**APPROVED).text.replace("2026-08-03T09:00:00", "bay-9-evening")

    with pytest.raises(InventedContentError):
        validate_sms(edited, **APPROVED)


def test_invented_urgency_is_rejected():
    edited = compose_sms(**APPROVED).text.replace("¿Confirma", "Es urgente. ¿Confirma")

    with pytest.raises(InventedContentError):
        validate_sms(edited, **APPROVED)


def test_missing_confirmation_request_is_rejected():
    edited = compose_sms(**APPROVED).text.replace("¿Confirma la cita?", "Gracias.")

    with pytest.raises(InventedContentError):
        validate_sms(edited, **APPROVED)


def test_more_than_three_segments_is_rejected():
    edited = compose_sms(**APPROVED).text + " Nota." * 120

    with pytest.raises(MessageTooLongError):
        validate_sms(edited, **APPROVED)


def test_reservation_is_deterministic_and_idempotent():
    store = AppointmentStore()
    booking = {
        "quote_id": "quote-1",
        "shop_id": "demo-shop",
        "demo_session_id": "session-1",
        "bay_slot_id": "bay-1-morning",
        "starts_at": "2026-08-03T09:00:00",
        "approver_role": "advisor",
    }

    first = store.reserve(**booking)
    repeat = store.reserve(**booking)

    assert first.id == repeat.id
    assert first.simulated is True
    assert store.for_quote("quote-1", "demo-shop", "session-1") == first


def test_reservation_is_scoped_to_the_demo_session():
    store = AppointmentStore()
    store.reserve(
        quote_id="quote-1",
        shop_id="demo-shop",
        demo_session_id="session-1",
        bay_slot_id="bay-1-morning",
        starts_at="2026-08-03T09:00:00",
        approver_role="advisor",
    )

    with pytest.raises(PermissionError):
        store.for_quote("quote-1", "demo-shop", "session-2")


def test_timeline_progresses_through_simulated_states():
    store = MessagingStore()
    delivery = store.enqueue(
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

    sent = store.advance(delivery.id, "demo-shop", "session-1")
    delivered = store.advance(delivery.id, "demo-shop", "session-1")

    assert (delivery.state, sent.state, delivered.state) == ("queued", "sent", "delivered")
    assert delivered.simulated is True
    assert delivered.text == delivery.text
    assert (delivered.approver_role, delivered.citation_page) == ("advisor", 42)
