from fastapi.testclient import TestClient

from service_advisor_api.main import app


def _headers(client: TestClient, role: str) -> dict[str, str]:
    session = client.post("/demo-sessions", json={"role": role})
    return {"Authorization": f"Bearer {session.json()['token']}"}


def test_manager_sees_the_full_canonical_matrix() -> None:
    client = TestClient(app)

    response = client.get("/admin/evaluation", headers=_headers(client, "manager"))

    body = response.json()
    assert response.status_code == 200
    assert body["case_count"] == 100
    assert body["scores"]["unsafe_sql"] == 1.0
    assert body["scores"]["prompt_injection"] == 1.0
    assert body["thresholds_met"] is True
    assert body["kinds"] == {"deterministic": 100}
    assert body["dataset_version"] == "canonical-100-v1"
    assert body["failing_case_ids"] == []


def test_advisors_cannot_read_the_evaluation_matrix() -> None:
    client = TestClient(app)

    response = client.get("/admin/evaluation", headers=_headers(client, "advisor"))

    assert response.status_code == 403
