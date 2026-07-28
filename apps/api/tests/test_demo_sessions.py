from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from service_advisor_api.auth import create_demo_session
from service_advisor_api.main import app


def _session_token(role: str = "advisor") -> str:
    response = TestClient(app).post("/demo-sessions", json={"role": role})

    assert response.status_code == 201
    return response.json()["token"]


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_protected_workspace_requires_a_valid_session() -> None:
    response = TestClient(app).get("/workspace")

    assert response.status_code == 401


def test_expired_session_cannot_access_the_workspace() -> None:
    token = create_demo_session("advisor", now=datetime.now(UTC) - timedelta(minutes=31))

    response = TestClient(app).get("/workspace", headers=_headers(token))

    assert response.status_code == 401
    assert response.json()["detail"] == "Demo session has expired"


def test_reset_affects_only_the_current_demo_session_overlay() -> None:
    first_token = _session_token()
    second_token = _session_token()
    client = TestClient(app)

    reset = client.post("/workspace/reset", headers=_headers(first_token))
    first_workspace = client.get("/workspace", headers=_headers(first_token))
    second_workspace = client.get("/workspace", headers=_headers(second_token))

    assert reset.status_code == 200
    assert first_workspace.json()["generation"] == 1
    assert second_workspace.json()["generation"] == 0
    assert first_workspace.json()["shop_id"] == second_workspace.json()["shop_id"] == "demo-shop"
    assert first_workspace.json()["demo_session_id"] != second_workspace.json()["demo_session_id"]


def test_advisor_cannot_access_admin_session_listing() -> None:
    response = TestClient(app).get("/admin/demo-sessions", headers=_headers(_session_token()))

    assert response.status_code == 403


def test_admin_can_access_admin_session_listing() -> None:
    client = TestClient(app)
    advisor_token = _session_token()
    client.get("/workspace", headers=_headers(advisor_token))
    response = client.get("/admin/demo-sessions", headers=_headers(_session_token("admin")))

    assert response.status_code == 200
    assert any(session["role"] == "advisor" for session in response.json())
