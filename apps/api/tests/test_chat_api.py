from fastapi.testclient import TestClient

from service_advisor_api.main import app


def test_contextual_chat_returns_grounded_citation() -> None:
    client = TestClient(app)
    token = client.post("/demo-sessions", json={"role": "advisor"}).json()["token"]

    response = client.post("/contextual-chat", headers={"Authorization": f"Bearer {token}"}, json={"question": "Why is this due?", "current_mileage_km": 48000, "provider_available": True})

    assert response.status_code == 200
    assert response.json()["citation_page"] == 42
    assert response.json()["degraded"] is False


def test_contextual_chat_degrades_after_bounded_provider_retry() -> None:
    client = TestClient(app)
    token = client.post("/demo-sessions", json={"role": "advisor"}).json()["token"]

    response = client.post("/contextual-chat", headers={"Authorization": f"Bearer {token}"}, json={"question": "Why?", "current_mileage_km": 48000, "provider_available": False})

    assert response.json()["degraded"] is True
    assert "temporarily unavailable" in response.json()["text"]
