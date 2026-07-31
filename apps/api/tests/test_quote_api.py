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


def _advisor_session(client: TestClient, *, with_checkin: bool = True) -> dict[str, str]:
    session = client.post("/demo-sessions", json={"role": "advisor"})
    headers = {"Authorization": f"Bearer {session.json()['token']}"}
    if with_checkin:
        client.post("/vehicles/honda-civic-2019-lx/check-ins", headers=headers, json=CHECKIN)
    return headers


def test_draft_prices_a_deduplicated_bundle_against_shop_operations() -> None:
    client = TestClient(app)
    headers = _advisor_session(client)

    response = client.post(
        "/vehicles/honda-civic-2019-lx/quote-drafts",
        headers=headers,
        json={"service_codes": ["HONDA-A1", "HONDA-TIRE-ROTATION"]},
    )

    body = response.json()
    assert response.status_code == 201
    assert body["lines"][0]["labor_mxn"] == "620.00"
    assert body["lines"][1]["labor_mxn"] == "0.00"
    assert body["iva_mxn"] == "254.88"
    assert body["total_mxn"] == "1847.88"
    assert body["duration_minutes"] == 50
    assert body["bay_slot_id"] == "bay-1-morning"


def test_draft_reports_an_explicit_unavailable_reason_from_inventory() -> None:
    client = TestClient(app)
    headers = _advisor_session(client)

    response = client.post(
        "/vehicles/honda-civic-2019-lx/quote-drafts",
        headers=headers,
        json={"service_codes": ["HONDA-CABIN-FILTER"]},
    )

    (line,) = response.json()["lines"]
    assert line["available"] is False
    assert line["unavailable_reason"] == "Part HON-CABIN-80292 is backordered until 2026-08-14"


def test_informational_service_cannot_be_drafted() -> None:
    client = TestClient(app)
    headers = _advisor_session(client)

    response = client.post(
        "/vehicles/honda-civic-2019-lx/quote-drafts",
        headers=headers,
        json={"service_codes": ["HONDA-MULTIPOINT-INSPECTION"]},
    )

    assert response.status_code == 422
    assert "informational only" in response.json()["detail"]


def test_draft_requires_a_confirmed_checkin() -> None:
    client = TestClient(app)
    headers = _advisor_session(client, with_checkin=False)

    response = client.post(
        "/vehicles/honda-civic-2019-lx/quote-drafts",
        headers=headers,
        json={"service_codes": ["HONDA-A1"]},
    )

    assert response.status_code == 409


def test_draft_requires_a_demo_session() -> None:
    response = TestClient(app).post(
        "/vehicles/honda-civic-2019-lx/quote-drafts",
        json={"service_codes": ["HONDA-A1"]},
    )

    assert response.status_code == 401
