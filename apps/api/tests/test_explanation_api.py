from fastapi.testclient import TestClient

from service_advisor_api.main import app


def _advisor_headers(client: TestClient) -> dict[str, str]:
    session = client.post("/demo-sessions", json={"role": "advisor"})
    return {"Authorization": f"Bearer {session.json()['token']}"}


def test_grounded_explanation_returns_only_citation_backed_content() -> None:
    client = TestClient(app)

    response = client.post(
        "/explanations",
        headers=_advisor_headers(client),
        json={
            "vehicle_id": "toyota-corolla-2022-le",
            "current_mileage_km": 40_000,
            "evidence_available": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["citation_page"] == 38
    assert response.json()["degraded"] is False


def test_explanation_follows_the_vehicle_on_screen() -> None:
    """What if the Advisor asks about the Corolla instead of the Civic the demo starts on?"""
    client = TestClient(app)
    headers = _advisor_headers(client)

    civic = client.post(
        "/explanations",
        headers=headers,
        json={
            "vehicle_id": "honda-civic-2019-lx",
            "current_mileage_km": 48_000,
            "evidence_available": True,
        },
    ).json()
    corolla = client.post(
        "/explanations",
        headers=headers,
        json={
            "vehicle_id": "toyota-corolla-2022-le",
            "current_mileage_km": 40_000,
            "evidence_available": True,
        },
    ).json()

    assert civic["degraded"] is True
    assert corolla["citation_page"] == 38
    assert "TOYOTA-10K" in corolla["text"]


def test_explanation_refuses_an_unknown_vehicle() -> None:
    client = TestClient(app)

    response = client.post(
        "/explanations",
        headers=_advisor_headers(client),
        json={
            "vehicle_id": "ghost-vehicle",
            "current_mileage_km": 40_000,
            "evidence_available": True,
        },
    )

    assert response.status_code == 404
