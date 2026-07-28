from fastapi.testclient import TestClient

from service_advisor_api.main import app


def _advisor_headers() -> dict[str, str]:
    client = TestClient(app)
    session = client.post("/demo-sessions", json={"role": "advisor"})
    return {"Authorization": f"Bearer {session.json()['token']}"}


def test_checkin_is_persisted_in_the_current_visitor_overlay() -> None:
    client = TestClient(app)
    headers = _advisor_headers()
    payload = {
        "current_mileage_km": 43_000,
        "checked_in_on": "2026-07-27",
        "use_profile": "severe",
        "severe_use_factors": ["traffic_and_idling"],
        "concern": "Brake pedal feels soft in traffic",
        "appointment_window": "2026-07-28 morning",
        "message_consent": True,
    }

    saved = client.post("/vehicles/honda-civic-2019-lx/check-ins", json=payload, headers=headers)
    summary = client.get("/vehicles/honda-civic-2019-lx/check-in", headers=headers)

    assert saved.status_code == 201
    assert summary.status_code == 200
    assert summary.json()["current_mileage_km"] == 43_000
    assert summary.json()["prior_mileage_km"] == 42_500
    assert summary.json()["severe_use_factors"] == ["traffic_and_idling"]


def test_invalid_checkin_cannot_be_saved() -> None:
    response = TestClient(app).post(
        "/vehicles/honda-civic-2019-lx/check-ins",
        json={
            "current_mileage_km": 42_499,
            "checked_in_on": "2026-07-27",
            "use_profile": "normal",
            "severe_use_factors": [],
            "concern": "",
            "appointment_window": "",
            "message_consent": False,
        },
        headers=_advisor_headers(),
    )

    assert response.status_code == 422
