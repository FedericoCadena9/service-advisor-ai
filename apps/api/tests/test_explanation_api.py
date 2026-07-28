from fastapi.testclient import TestClient

from service_advisor_api.main import app


def test_grounded_explanation_returns_only_citation_backed_content() -> None:
    client = TestClient(app)
    session = client.post("/demo-sessions", json={"role": "advisor"})
    headers = {"Authorization": f"Bearer {session.json()['token']}"}
    response = client.post("/explanations", headers=headers, json={"current_mileage_km": 48000, "evidence_available": True})

    assert response.status_code == 200
    assert response.json()["citation_page"] == 42
    assert response.json()["degraded"] is False
