from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from service_advisor_api.main import app, operations_store

CHECKIN = {
    "current_mileage_km": 48_000,
    "checked_in_on": "2026-07-27",
    "use_profile": "normal",
    "severe_use_factors": [],
    "concern": "Service due",
    "appointment_window": "Tomorrow",
    "message_consent": True,
}


@pytest.fixture
def restore_inventory() -> Iterator[None]:
    yield
    operations_store.set_part_on_hand("demo-shop", "HON-FILTER-15400", 4)


def _advisor_session(client: TestClient) -> dict[str, str]:
    session = client.post("/demo-sessions", json={"role": "advisor"})
    headers = {"Authorization": f"Bearer {session.json()['token']}"}
    client.post("/vehicles/honda-civic-2019-lx/check-ins", headers=headers, json=CHECKIN)
    return headers


def _open_review(client: TestClient, headers: dict[str, str]) -> dict[str, object]:
    response = client.post(
        "/vehicles/honda-civic-2019-lx/quote-reviews",
        headers=headers,
        json={"service_codes": ["HONDA-A1"]},
    )
    assert response.status_code == 201
    return response.json()


def test_review_identifies_approver_services_facts_and_citations() -> None:
    client = TestClient(app)
    headers = _advisor_session(client)

    review = _open_review(client, headers)

    assert review["approver_role"] == "advisor"
    assert review["approver_session_id"]
    assert review["facts"]["service_codes"] == ["HONDA-A1"]
    assert review["facts"]["total_mxn"] == "1847.88"
    assert review["facts"]["bay_slot_id"] == "bay-1-morning"
    assert review["citations"] == {
        "rule_version": "honda-civic-2019-lx-us-v1",
        "citation_page": 1,
        "citation_section": "Maintenance Minder Service Codes",
    }
    assert review["status"] == "in_review"


def test_repeated_approval_returns_the_same_saved_quote() -> None:
    client = TestClient(app)
    headers = _advisor_session(client)
    review = _open_review(client, headers)

    first = client.post(
        f"/quote-reviews/{review['id']}/decision",
        headers=headers,
        json={"decision": "approve", "idempotency_key": "key-1"},
    )
    repeat = client.post(
        f"/quote-reviews/{review['id']}/decision",
        headers=headers,
        json={"decision": "approve", "idempotency_key": "key-1"},
    )

    assert first.status_code == 200
    assert first.json()["quote_id"] == repeat.json()["quote_id"]
    assert first.json()["approver_role"] == "advisor"


def test_inventory_change_invalidates_the_quote_and_returns_it_to_review(
    restore_inventory: None,
) -> None:
    client = TestClient(app)
    headers = _advisor_session(client)
    review = _open_review(client, headers)
    operations_store.set_part_on_hand(
        "demo-shop", "HON-FILTER-15400", 0, restock_status="backordered", restock_eta="2026-08-20"
    )

    approval = client.post(
        f"/quote-reviews/{review['id']}/decision",
        headers=headers,
        json={"decision": "approve", "idempotency_key": "key-1"},
    )
    reloaded = client.get(f"/quote-reviews/{review['id']}", headers=headers)

    assert approval.status_code == 409
    assert reloaded.json()["status"] == "in_review"
    assert reloaded.json()["invalidation_reason"] == (
        "Volatile pricing, inventory, or slot inputs changed"
    )
    assert reloaded.json()["facts"]["total_mxn"] == "0.00"


def test_rejection_is_recorded_with_a_reason_and_saves_no_quote() -> None:
    client = TestClient(app)
    headers = _advisor_session(client)
    review = _open_review(client, headers)

    response = client.post(
        f"/quote-reviews/{review['id']}/decision",
        headers=headers,
        json={
            "decision": "reject",
            "idempotency_key": "key-1",
            "reason": "Customer declined the bundle",
        },
    )

    assert response.status_code == 200
    assert response.json()["quote_id"] is None
    assert response.json()["reason"] == "Customer declined the bundle"


def test_rejection_requires_a_reason() -> None:
    client = TestClient(app)
    headers = _advisor_session(client)
    review = _open_review(client, headers)

    response = client.post(
        f"/quote-reviews/{review['id']}/decision",
        headers=headers,
        json={"decision": "reject", "idempotency_key": "key-1", "reason": "  "},
    )

    assert response.status_code == 422


def test_review_from_another_demo_session_is_not_found() -> None:
    client = TestClient(app)
    review = _open_review(client, _advisor_session(client))

    response = client.get(f"/quote-reviews/{review['id']}", headers=_advisor_session(client))

    assert response.status_code == 404
