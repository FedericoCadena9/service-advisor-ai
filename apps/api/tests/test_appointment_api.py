from fastapi.testclient import TestClient

from service_advisor_api.main import app

CHECKIN = {
    "current_mileage_km": 48_000,
    "checked_in_on": "2026-07-27",
    "use_profile": "normal",
    "severe_use_factors": [],
    "concern": "Service due",
    "appointment_window": "Tomorrow",
    "message_consent": True,
}


def _approved_quote(client: TestClient) -> tuple[dict[str, str], str]:
    session = client.post("/demo-sessions", json={"role": "advisor"})
    headers = {"Authorization": f"Bearer {session.json()['token']}"}
    client.post("/vehicles/honda-civic-2019-lx/check-ins", headers=headers, json=CHECKIN)
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
    return headers, decision["quote_id"]


def test_reservation_requires_a_valid_human_approval() -> None:
    client = TestClient(app)
    session = client.post("/demo-sessions", json={"role": "advisor"})
    headers = {"Authorization": f"Bearer {session.json()['token']}"}

    response = client.post("/quotes/unapproved-quote/appointment", headers=headers)

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "A human approval is required before reserving or messaging"
    )


def test_reservation_is_idempotent_and_labeled_simulated() -> None:
    client = TestClient(app)
    headers, quote_id = _approved_quote(client)

    first = client.post(f"/quotes/{quote_id}/appointment", headers=headers)
    repeat = client.post(f"/quotes/{quote_id}/appointment", headers=headers)

    assert first.status_code == 201
    assert first.json()["id"] == repeat.json()["id"]
    assert first.json()["bay_slot_id"] == "bay-1-morning"
    assert first.json()["simulated"] is True


def test_preview_and_timeline_preserve_approved_text_citations_and_approver() -> None:
    client = TestClient(app)
    headers, quote_id = _approved_quote(client)
    client.post(f"/quotes/{quote_id}/appointment", headers=headers)

    preview = client.post(f"/quotes/{quote_id}/sms-preview", headers=headers).json()
    enqueued = client.post(
        f"/quotes/{quote_id}/messages", headers=headers, json={"text": preview["text"]}
    )
    sent = client.post(f"/messages/{enqueued.json()['id']}/advance", headers=headers)
    delivered = client.post(f"/messages/{enqueued.json()['id']}/advance", headers=headers)

    assert 1 <= preview["segments"] <= 3
    assert len(preview["priorities"]) <= 3
    assert enqueued.json()["state"] == "queued"
    assert (sent.json()["state"], delivered.json()["state"]) == ("sent", "delivered")
    assert delivered.json()["simulated"] is True
    assert delivered.json()["text"] == preview["text"]
    assert delivered.json()["approver_role"] == "advisor"
    assert delivered.json()["citation_page"] == 1


def test_edited_message_that_invents_a_price_is_rejected() -> None:
    client = TestClient(app)
    headers, quote_id = _approved_quote(client)
    client.post(f"/quotes/{quote_id}/appointment", headers=headers)
    preview = client.post(f"/quotes/{quote_id}/sms-preview", headers=headers).json()

    response = client.post(
        f"/quotes/{quote_id}/messages",
        headers=headers,
        json={"text": preview["text"].replace("1,847.88", "5,000.00")},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Message states a price the approved quote does not contain"
    )


def test_message_requires_a_reserved_appointment() -> None:
    client = TestClient(app)
    headers, quote_id = _approved_quote(client)
    preview = client.post(f"/quotes/{quote_id}/sms-preview", headers=headers).json()

    response = client.post(
        f"/quotes/{quote_id}/messages", headers=headers, json={"text": preview["text"]}
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Reserve the appointment before enqueueing a message"


def test_message_is_not_visible_to_another_demo_session() -> None:
    client = TestClient(app)
    headers, quote_id = _approved_quote(client)
    client.post(f"/quotes/{quote_id}/appointment", headers=headers)
    preview = client.post(f"/quotes/{quote_id}/sms-preview", headers=headers).json()
    enqueued = client.post(
        f"/quotes/{quote_id}/messages", headers=headers, json={"text": preview["text"]}
    ).json()
    other = client.post("/demo-sessions", json={"role": "advisor"})

    response = client.get(
        f"/messages/{enqueued['id']}",
        headers={"Authorization": f"Bearer {other.json()['token']}"},
    )

    assert response.status_code == 404
