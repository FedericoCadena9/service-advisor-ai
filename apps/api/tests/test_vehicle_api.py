from fastapi.testclient import TestClient

from service_advisor_api.main import app


def _advisor_headers() -> dict[str, str]:
    client = TestClient(app)
    session = client.post("/demo-sessions", json={"role": "advisor"})
    return {"Authorization": f"Bearer {session.json()['token']}"}


def test_advisor_can_search_safe_canonical_vehicle_fields() -> None:
    response = TestClient(app).get("/vehicles/search", params={"query": "civic"}, headers=_advisor_headers())

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": "honda-civic-2019-lx",
            "customer_label": "Demo Customer",
            "vehicle_label": "2019 Honda Civic LX 2.0L Mexico",
            "is_demo_data": True,
        }
    ]


def test_advisor_can_open_the_seeded_vehicle_workspace_summary() -> None:
    response = TestClient(app).get("/vehicles/honda-civic-2019-lx", headers=_advisor_headers())

    assert response.status_code == 200
    assert response.json()["prior_mileage_km"] == 42_500
    assert response.json()["prior_mileage_recorded_on"] == "2026-06-15"
    assert response.json()["is_demo_data"] is True
