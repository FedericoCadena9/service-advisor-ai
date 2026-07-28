from fastapi.testclient import TestClient

from service_advisor_api.main import app


def test_advisor_reads_completed_and_declined_history_separately() -> None:
    client = TestClient(app)
    session = client.post("/demo-sessions", json={"role": "advisor"})

    response = client.get(
        "/vehicles/honda-civic-2019-lx/history",
        headers={"Authorization": f"Bearer {session.json()['token']}"},
    )

    assert response.status_code == 200
    assert response.json()["completed"][0]["status"] == "completed"
    assert response.json()["declined"][0]["status"] == "declined"
