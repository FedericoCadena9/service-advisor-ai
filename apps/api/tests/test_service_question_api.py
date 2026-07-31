from fastapi.testclient import TestClient

from service_advisor_api.main import app


def _advisor_headers(client: TestClient) -> dict[str, str]:
    session = client.post("/demo-sessions", json={"role": "advisor"})
    return {"Authorization": f"Bearer {session.json()['token']}"}


def test_supported_question_returns_the_accepted_sql_and_metadata() -> None:
    client = TestClient(app)

    response = client.post(
        "/service-questions",
        headers=_advisor_headers(client),
        json={"question": "Which parts are on backorder?"},
    )

    body = response.json()
    assert response.status_code == 200
    assert body["sql"].startswith("SELECT part_number, on_hand, restock_status")
    assert body["sql"].endswith("LIMIT 100")
    assert body["retrieval"] == {
        "views": ["v_parts_availability"],
        "columns": ["part_number", "on_hand", "restock_status"],
        "row_limit": 100,
        "timeout_seconds": 2.0,
        "principal": "semantic_reader",
    }
    assert body["answer"].startswith("Parts availability:")


def test_answers_never_expose_personal_data() -> None:
    client = TestClient(app)

    response = client.post(
        "/service-questions",
        headers=_advisor_headers(client),
        json={"question": "How many services were declined?"},
    )

    assert "Demo Customer" not in response.text
    assert "+52" not in response.text


def test_unsupported_question_is_refused() -> None:
    client = TestClient(app)

    response = client.post(
        "/service-questions",
        headers=_advisor_headers(client),
        json={"question": "Give me the customer phone number"},
    )

    assert response.status_code == 422


def test_service_questions_require_a_demo_session() -> None:
    response = TestClient(app).post("/service-questions", json={"question": "declined services"})

    assert response.status_code == 401
