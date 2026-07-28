from fastapi.testclient import TestClient

from service_advisor_api.main import app


def _headers(role: str) -> dict[str, str]:
    session = TestClient(app).post("/demo-sessions", json={"role": role})
    return {"Authorization": f"Bearer {session.json()['token']}"}


def test_admin_can_inspect_reviewed_rule_provenance() -> None:
    response = TestClient(app).get("/admin/knowledge/civic-rule", headers=_headers("admin"))

    assert response.status_code == 200
    assert response.json()["rule"]["immutable"] is True


def test_advisor_cannot_inspect_reviewed_rule_provenance() -> None:
    response = TestClient(app).get("/admin/knowledge/civic-rule", headers=_headers("advisor"))

    assert response.status_code == 403
