"""Interrupted queries and half-finished journeys."""

import time
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from service_advisor_api.main import app, operations_store
from service_advisor_api.text_to_sql import (
    QueryFailedError,
    QueryTimeoutError,
    SemanticQueryGateway,
    UnsafeSqlError,
    validate_sql,
)

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
def gateway() -> SemanticQueryGateway:
    store = SemanticQueryGateway()
    store.seed()
    return store


@pytest.fixture
def restore_inventory() -> Iterator[None]:
    yield
    operations_store.set_part_on_hand("demo-shop", "HON-FILTER-15400", 4)


# Interrupted queries


def test_a_query_that_outruns_its_budget_is_interrupted(gateway: SemanticQueryGateway) -> None:
    """What if the query never finishes instead of returning in milliseconds?"""
    accepted = validate_sql("SELECT service_code FROM v_service_history")
    expired = type(accepted)(
        sql=accepted.sql,
        views=accepted.views,
        columns=accepted.columns,
        row_limit=accepted.row_limit,
        timeout_seconds=-1.0,
        principal=accepted.principal,
    )

    with pytest.raises(QueryTimeoutError):
        gateway.execute(expired, "demo-shop")


def test_the_tenant_is_cleared_after_an_interrupted_query(
    gateway: SemanticQueryGateway,
) -> None:
    """What if a query dies mid-flight — can the next caller inherit its tenant?"""
    accepted = validate_sql("SELECT part_number FROM v_parts_availability")
    expired = type(accepted)(
        sql=accepted.sql,
        views=accepted.views,
        columns=accepted.columns,
        row_limit=accepted.row_limit,
        timeout_seconds=-1.0,
        principal=accepted.principal,
    )
    with pytest.raises(QueryTimeoutError):
        gateway.execute(expired, "other-shop")

    rows = gateway.execute(accepted, "demo-shop")

    assert rows == (("HON-OIL-0W20",), ("HON-CABIN-80292",))


def test_the_connection_survives_an_interrupted_query(gateway: SemanticQueryGateway) -> None:
    """What if the interrupt leaves the connection unusable for everyone after it?"""
    accepted = validate_sql("SELECT service_code FROM v_service_history")
    expired = type(accepted)(
        sql=accepted.sql,
        views=accepted.views,
        columns=accepted.columns,
        row_limit=accepted.row_limit,
        timeout_seconds=-1.0,
        principal=accepted.principal,
    )
    with pytest.raises(QueryTimeoutError):
        gateway.execute(expired, "demo-shop")

    assert len(gateway.execute(accepted, "demo-shop")) == 2


def test_a_write_forged_past_validation_cannot_reach_the_database(
    gateway: SemanticQueryGateway,
) -> None:
    """What if the connection's read-only pragma is the last line standing?"""
    accepted = validate_sql("SELECT service_code FROM v_service_history")
    write = type(accepted)(
        sql="UPDATE base_quotes SET total_mxn = '0.00'",
        views=accepted.views,
        columns=accepted.columns,
        row_limit=accepted.row_limit,
        timeout_seconds=accepted.timeout_seconds,
        principal=accepted.principal,
    )

    with pytest.raises((UnsafeSqlError, QueryFailedError)):
        gateway.execute(write, "demo-shop")


def test_the_timeout_is_reported_as_504_to_the_advisor(monkeypatch: pytest.MonkeyPatch) -> None:
    client = TestClient(app)
    session = client.post("/demo-sessions", json={"role": "advisor"})

    def slow(*args: object, **kwargs: object) -> None:
        raise QueryTimeoutError("The query exceeded the strict timeout")

    monkeypatch.setattr("service_advisor_api.main.semantic_gateway.run", slow)
    response = client.post(
        "/service-questions",
        headers={"Authorization": f"Bearer {session.json()['token']}"},
        json={"question": "Which parts are on backorder?"},
    )

    assert response.status_code == 504


# Half-finished journeys


def _advisor(client: TestClient) -> dict[str, str]:
    session = client.post("/demo-sessions", json={"role": "advisor"})
    headers = {"Authorization": f"Bearer {session.json()['token']}"}
    client.post("/vehicles/honda-civic-2019-lx/check-ins", headers=headers, json=CHECKIN)
    return headers


def _approved_quote(client: TestClient, headers: dict[str, str]) -> str:
    review = client.post(
        "/vehicles/honda-civic-2019-lx/quote-reviews",
        headers=headers,
        json={"service_codes": ["HONDA-A1"]},
    ).json()
    decision = client.post(
        f"/quote-reviews/{review['id']}/decision",
        headers=headers,
        json={"decision": "approve", "idempotency_key": "key-1"},
    ).json()
    return decision["quote_id"]


def test_an_approval_left_without_a_reservation_stops_being_reservable(
    restore_inventory: None,
) -> None:
    """What if the Advisor is interrupted between approving and reserving?"""
    client = TestClient(app)
    headers = _advisor(client)
    quote_id = _approved_quote(client, headers)
    operations_store.set_part_on_hand(
        "demo-shop", "HON-FILTER-15400", 0, restock_status="backordered", restock_eta="2026-08-20"
    )
    client.get(f"/quote-reviews/{_review_of(client, headers)}", headers=headers)

    response = client.post(f"/quotes/{quote_id}/appointment", headers=headers)

    assert response.status_code == 409


def _review_of(client: TestClient, headers: dict[str, str]) -> str:
    audit = client.get("/quote-audit", headers=_manager(client)).json()
    return audit[-1]["review_id"]


def _manager(client: TestClient) -> dict[str, str]:
    session = client.post("/demo-sessions", json={"role": "manager"})
    return {"Authorization": f"Bearer {session.json()['token']}"}


def test_a_reservation_without_a_message_can_still_be_messaged() -> None:
    """What if the message step fails after the slot was already held?"""
    client = TestClient(app)
    headers = _advisor(client)
    quote_id = _approved_quote(client, headers)
    client.post(f"/quotes/{quote_id}/appointment", headers=headers)
    preview = client.post(f"/quotes/{quote_id}/sms-preview", headers=headers).json()

    rejected = client.post(
        f"/quotes/{quote_id}/messages", headers=headers, json={"text": "texto inventado"}
    )
    retried = client.post(
        f"/quotes/{quote_id}/messages", headers=headers, json={"text": preview["text"]}
    )

    assert rejected.status_code == 422
    assert retried.status_code == 201
    assert retried.json()["state"] == "queued"


def test_a_check_in_survives_a_failed_recommendation() -> None:
    """What if the recommendation call fails after the check-in was saved?"""
    client = TestClient(app)
    headers = _advisor(client)

    missing = client.get("/vehicles/ghost-vehicle/recommendation", headers=headers)
    saved = client.get("/vehicles/honda-civic-2019-lx/check-in", headers=headers)

    assert missing.status_code == 404
    assert saved.status_code == 200
    assert saved.json()["current_mileage_km"] == 48_000


def test_two_quotes_for_one_vehicle_do_not_share_an_appointment() -> None:
    """What if a second quote is approved while the first already holds the slot?"""
    client = TestClient(app)
    headers = _advisor(client)
    first_quote = _approved_quote(client, headers)
    client.post(f"/quotes/{first_quote}/appointment", headers=headers)

    second_review = client.post(
        "/vehicles/honda-civic-2019-lx/quote-reviews",
        headers=headers,
        json={"service_codes": ["HONDA-TIRE-ROTATION"]},
    ).json()
    second_decision = client.post(
        f"/quote-reviews/{second_review['id']}/decision",
        headers=headers,
        json={"decision": "approve", "idempotency_key": "key-2"},
    ).json()
    second_appointment = client.post(
        f"/quotes/{second_decision['quote_id']}/appointment", headers=headers
    )

    assert second_appointment.status_code == 201
    assert second_appointment.json()["id"] != first_quote


def test_the_gateway_stays_usable_under_repeated_failures(gateway: SemanticQueryGateway) -> None:
    """What if a burst of bad queries arrives instead of one?"""
    accepted = validate_sql("SELECT service_code FROM v_service_history")
    broken = type(accepted)(
        sql="SELECT nope FROM v_service_history LIMIT 1",
        views=accepted.views,
        columns=accepted.columns,
        row_limit=1,
        timeout_seconds=accepted.timeout_seconds,
        principal=accepted.principal,
    )
    started = time.monotonic()

    for _ in range(20):
        with pytest.raises(QueryFailedError):
            gateway.execute(broken, "demo-shop")

    assert len(gateway.execute(accepted, "demo-shop")) == 2
    assert time.monotonic() - started < 5
