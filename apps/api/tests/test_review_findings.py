"""Regression tests for the code-review findings on the #11-#22 round."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from test_approvals import CITATIONS, FACTS, NO_ESCALATION

from service_advisor_api.approvals import (
    AlreadyDecidedError,
    QuoteCommandStore,
    QuoteFacts,
    StaleQuoteError,
)
from service_advisor_api.evaluation import build_corpus, run_suite
from service_advisor_api.knowledge import KnowledgePack
from service_advisor_api.main import app, operations_store
from service_advisor_api.quotes import catalog_service
from service_advisor_api.vehicles import CanonicalVehicleStore
from service_advisor_api.voice import transcribe

CHECKIN = {
    "current_mileage_km": 48_000,
    "checked_in_on": "2026-07-31",
    "use_profile": "normal",
    "severe_use_factors": [],
    "concern": "Servicio programado",
    "appointment_window": "Manana",
    "message_consent": True,
}


@pytest.fixture
def restore_inventory() -> Iterator[None]:
    yield
    operations_store.set_part_on_hand("demo-shop", "HON-FILTER-15400", 4)


def _store_with_review(now: datetime | None = None) -> tuple[QuoteCommandStore, str]:
    store = QuoteCommandStore()
    review = store.open_review(
        shop_id="demo-shop",
        demo_session_id="session-1",
        vehicle_id="honda-civic-2019-lx",
        facts=FACTS,
        citations=CITATIONS,
        fingerprint="fingerprint-a",
        now=now,
    )
    return store, review.id


def _approve(store: QuoteCommandStore, review_id: str, **overrides):
    arguments = {
        "shop_id": "demo-shop",
        "demo_session_id": "session-1",
        "approver_role": "advisor",
        "approver_session_id": "session-1",
        "idempotency_key": "key-1",
        "current_facts": FACTS,
        "current_fingerprint": "fingerprint-a",
        "escalation": NO_ESCALATION,
    }
    return store.approve(review_id, **{**arguments, **overrides})


def test_an_invalidated_approval_can_no_longer_be_used_downstream() -> None:
    """What if the parts price changes after approval instead of before it?"""
    store, review_id = _store_with_review()
    decision = _approve(store, review_id)
    repriced = QuoteFacts(**{**FACTS.__dict__, "total_mxn": FACTS.total_mxn + 1})

    store.revalidate(review_id, repriced, "fingerprint-b")

    with pytest.raises(StaleQuoteError):
        store.approved_quote(
            decision.quote_id or "", shop_id="demo-shop", demo_session_id="session-1"
        )


def test_rejecting_an_approved_quote_is_refused_instead_of_reported_as_approved() -> None:
    """What if the Advisor rejects after approving, instead of before?"""
    store, review_id = _store_with_review()
    _approve(store, review_id)

    with pytest.raises(AlreadyDecidedError):
        store.reject(
            review_id,
            shop_id="demo-shop",
            demo_session_id="session-1",
            approver_role="advisor",
            approver_session_id="session-1",
            reason="Customer changed their mind",
        )


def test_an_expired_quote_cannot_be_approved() -> None:
    """What if the Advisor approves a day later instead of during the visit?"""
    opened_at = datetime(2026, 7, 31, 9, 0, tzinfo=UTC)
    store, review_id = _store_with_review(now=opened_at)

    with pytest.raises(StaleQuoteError, match="expired"):
        _approve(store, review_id, now=opened_at + timedelta(hours=25))


def test_an_expired_approval_cannot_reserve_or_message() -> None:
    """What if the approved quote is acted on after its expiry instead of inside it?"""
    opened_at = datetime(2026, 7, 31, 9, 0, tzinfo=UTC)
    store, review_id = _store_with_review(now=opened_at)
    decision = _approve(store, review_id, now=opened_at)

    with pytest.raises(StaleQuoteError, match="expired"):
        store.approved_quote(
            decision.quote_id or "",
            shop_id="demo-shop",
            demo_session_id="session-1",
            now=opened_at + timedelta(hours=25),
        )


def test_review_reports_its_expiry_to_the_advisor() -> None:
    client = TestClient(app)
    session = client.post("/demo-sessions", json={"role": "advisor"})
    headers = {"Authorization": f"Bearer {session.json()['token']}"}
    client.post("/vehicles/honda-civic-2019-lx/check-ins", headers=headers, json=CHECKIN)

    review = client.post(
        "/vehicles/honda-civic-2019-lx/quote-reviews",
        headers=headers,
        json={"service_codes": ["HONDA-A1"]},
    ).json()

    assert datetime.fromisoformat(review["expires_at"]) > datetime.now(UTC)


def test_every_reviewed_rule_has_a_quotable_service() -> None:
    """What if the Advisor opens a Ranger instead of the Civic the demo was built around?"""
    for configuration in KnowledgePack().configurations():
        service = catalog_service(configuration.rule.service_code)
        assert service.informational_only is False
        assert configuration.engine in service.fits_engines


def test_each_canonical_vehicle_can_be_quoted_through_the_api() -> None:
    client = TestClient(app)
    session = client.post("/demo-sessions", json={"role": "advisor"})
    headers = {"Authorization": f"Bearer {session.json()['token']}"}
    pack = KnowledgePack()

    for row in CanonicalVehicleStore.SEED_ROWS:
        vehicle_id = str(row[1])
        _, rule = pack.rule_for(
            make=str(row[4]),
            model=str(row[5]),
            engine=str(row[7]),
            drivetrain=str(row[8]),
            market=str(row[9]),
            allow_fallback_market=True,
        )
        client.post(
            f"/vehicles/{vehicle_id}/check-ins",
            headers=headers,
            json={**CHECKIN, "current_mileage_km": rule.interval_km},
        )

        response = client.post(
            f"/vehicles/{vehicle_id}/quote-drafts",
            headers=headers,
            json={"service_codes": [rule.service_code]},
        )

        assert response.status_code == 201, vehicle_id
        (line,) = response.json()["lines"]
        assert line["available"] is True, (vehicle_id, line["unavailable_reason"])


def test_unconfirmed_audio_is_still_bounded_by_the_recovery_limit() -> None:
    """What if the Advisor never confirms the transcript instead of confirming it?"""
    note = transcribe(
        shop_id="demo-shop",
        demo_session_id="session-1",
        language="es",
        duration_seconds=42.0,
        consent=True,
        provider_available=True,
        now=datetime(2026, 7, 31, 12, 0, tzinfo=UTC),
    )

    assert note.state == "transcribed"
    assert note.audio_retained is True
    assert note.audio_retention_expires_at == "2026-08-01T12:00:00+00:00"


def test_a_live_model_run_cannot_grade_its_own_security_cases() -> None:
    """What if the live model answers the attack cases instead of the validators?"""
    corpus = build_corpus()

    report = run_suite(corpus, live_model=lambda case: True, provider="claude-opus-5")

    security = [
        result
        for result in report.results
        if result.archetype in ("unsafe_sql", "prompt_injection")
    ]
    assert security
    assert all(result.kind == "deterministic" for result in security)
    assert report.kinds["live_model"] == len(corpus) - len(security)


def test_a_dishonest_live_model_still_fails_the_security_gate() -> None:
    corpus = [case for case in build_corpus() if case.archetype == "unsafe_sql"]

    report = run_suite(corpus, live_model=lambda case: False, provider="claude-opus-5")

    assert report.scores["unsafe_sql"] == 1.0
    assert report.kinds == {"deterministic": len(corpus)}


def test_evaluation_grades_the_path_the_product_actually_takes() -> None:
    """What if the Tacoma only has a US document instead of a Mexican one?"""
    tacoma = [
        case
        for case in build_corpus()
        if case.vehicle_id == "toyota-tacoma-2020-sr5" and case.archetype == "due_now"
    ]

    (case,) = tacoma
    assert case.requires_fallback_review is True
    assert case.expected_state == "informational"
    assert case.expected_service_code is None
