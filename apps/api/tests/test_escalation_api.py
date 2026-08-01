from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from service_advisor_api.main import app, operations_store, service_history_store
from service_advisor_api.service_history import ServiceRecord

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
def repeated_decline() -> Iterator[None]:
    service_history_store.add_record(
        "demo-shop",
        "honda-civic-2019-lx",
        ServiceRecord("decline-honda-a1-2026-07", "HONDA-A1", "declined"),
    )
    yield
    service_history_store.remove_record(
        "demo-shop", "honda-civic-2019-lx", "decline-honda-a1-2026-07"
    )


@pytest.fixture
def restore_inventory() -> Iterator[None]:
    yield
    operations_store.set_part_on_hand("demo-shop", "HON-FILTER-15400", 4)


def _session(client: TestClient, role: str) -> dict[str, str]:
    session = client.post("/demo-sessions", json={"role": role})
    headers = {"Authorization": f"Bearer {session.json()['token']}"}
    client.post("/vehicles/honda-civic-2019-lx/check-ins", headers=headers, json=CHECKIN)
    return headers


def _open_review(client: TestClient, headers: dict[str, str], service_codes: list[str]) -> dict:
    response = client.post(
        "/vehicles/honda-civic-2019-lx/quote-reviews",
        headers=headers,
        json={"service_codes": service_codes},
    )
    assert response.status_code == 201
    return response.json()


def test_review_reports_the_escalation_condition_before_any_command(
    repeated_decline: None,
) -> None:
    client = TestClient(app)

    review = _open_review(client, _session(client, "advisor"), ["HONDA-A1"])

    assert review["escalation_required"] is True
    assert review["escalation_reasons"] == ["Customer repeatedly declined a quoted service"]


def test_advisor_cannot_approve_an_escalated_quote(repeated_decline: None) -> None:
    client = TestClient(app)
    headers = _session(client, "advisor")
    review = _open_review(client, headers, ["HONDA-A1"])

    response = client.post(
        f"/quote-reviews/{review['id']}/decision",
        headers=headers,
        json={"decision": "approve", "idempotency_key": "key-1", "reason": "Customer agreed"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "A Manager must decide this escalated quote"


def test_manager_approval_records_reason_snapshot_and_citations(repeated_decline: None) -> None:
    client = TestClient(app)
    headers = _session(client, "manager")
    review = _open_review(client, headers, ["HONDA-A1"])

    response = client.post(
        f"/quote-reviews/{review['id']}/decision",
        headers=headers,
        json={
            "decision": "approve",
            "idempotency_key": "key-1",
            "reason": "Customer accepted after a second decline",
        },
    )

    decision = response.json()
    assert response.status_code == 200
    assert decision["approver_role"] == "manager"
    assert decision["reason"] == "Customer accepted after a second decline"
    assert decision["escalation_reasons"] == ["Customer repeatedly declined a quoted service"]
    assert decision["facts"]["total_mxn"] == "1847.88"
    assert decision["citations"]["citation_page"] == 1


def test_escalated_approval_requires_a_recorded_reason(repeated_decline: None) -> None:
    client = TestClient(app)
    headers = _session(client, "manager")
    review = _open_review(client, headers, ["HONDA-A1"])

    response = client.post(
        f"/quote-reviews/{review['id']}/decision",
        headers=headers,
        json={"decision": "approve", "idempotency_key": "key-1"},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "An escalated quote requires a recorded reason"


def test_unavailable_operations_escalate_to_a_manager() -> None:
    client = TestClient(app)
    headers = _session(client, "advisor")
    review = _open_review(client, headers, ["HONDA-CABIN-FILTER"])

    assert review["escalation_reasons"] == [
        "Unavailable operations exception: HONDA-CABIN-FILTER"
    ]


def test_changed_operational_inputs_escalate_after_invalidation(
    restore_inventory: None,
) -> None:
    client = TestClient(app)
    headers = _session(client, "advisor")
    review = _open_review(client, headers, ["HONDA-A1"])
    operations_store.set_part_on_hand(
        "demo-shop", "HON-FILTER-15400", 0, restock_status="backordered", restock_eta="2026-08-20"
    )

    stale = client.post(
        f"/quote-reviews/{review['id']}/decision",
        headers=headers,
        json={"decision": "approve", "idempotency_key": "key-1"},
    )
    retry = client.post(
        f"/quote-reviews/{review['id']}/decision",
        headers=headers,
        json={"decision": "approve", "idempotency_key": "key-2", "reason": "Customer waits"},
    )

    assert stale.status_code == 409
    assert retry.status_code == 403


def test_audit_trail_is_manager_only_and_append_only() -> None:
    client = TestClient(app)
    advisor = _session(client, "advisor")
    review = _open_review(client, advisor, ["HONDA-A1"])
    client.post(
        f"/quote-reviews/{review['id']}/decision",
        headers=advisor,
        json={"decision": "approve", "idempotency_key": "key-1"},
    )
    client.post(
        f"/quote-reviews/{review['id']}/decision",
        headers=advisor,
        json={"decision": "approve", "idempotency_key": "key-2"},
    )

    forbidden = client.get("/quote-audit", headers=advisor)
    audit = client.get("/quote-audit", headers=_session(client, "manager"))

    entries = [entry for entry in audit.json() if entry["review_id"] == review["id"]]
    assert forbidden.status_code == 403
    assert audit.status_code == 200
    assert len(entries) == 1
    assert entries[0]["approver_role"] == "advisor"
    assert entries[0]["citations"]["rule_version"] == "honda-civic-2019-lx-us-v1"
