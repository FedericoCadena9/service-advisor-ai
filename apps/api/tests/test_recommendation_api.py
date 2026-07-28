from fastapi.testclient import TestClient

from service_advisor_api.main import app


def test_recommendation_requires_a_confirmed_checkin_and_returns_citation() -> None:
    client = TestClient(app)
    session = client.post("/demo-sessions", json={"role": "advisor"})
    headers = {"Authorization": f"Bearer {session.json()['token']}"}
    client.post(
        "/vehicles/honda-civic-2019-lx/check-ins",
        headers=headers,
        json={"current_mileage_km": 48000, "checked_in_on": "2026-07-27", "use_profile": "normal", "severe_use_factors": [], "concern": "Service", "appointment_window": "Tomorrow", "message_consent": True},
    )

    response = client.get("/vehicles/honda-civic-2019-lx/recommendation", headers=headers)

    assert response.status_code == 200
    assert response.json()["state"] == "completed"
    assert response.json()["citation_page"] == 42
    assert response.json()["declined_service_ids"] == ["decline-honda-a1-2026-06"]
