from fastapi.testclient import TestClient

from service_advisor_api.main import app


def test_health_reports_a_healthy_demo_environment() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
