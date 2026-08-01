import pytest
from fastapi.testclient import TestClient

from service_advisor_api import main
from service_advisor_api.main import app
from service_advisor_api.providers import ProviderUnavailableError

QUESTION = {
    "question": "¿Por que es necesario?",
    "vehicle_id": "toyota-corolla-2022-le",
    "current_mileage_km": 40_000,
}


class StubProvider:
    name = "stub"

    def __init__(self, answer: str | None = None, error: Exception | None = None) -> None:
        self._answer = answer
        self._error = error

    def complete(self, prompt: str, *, timeout_seconds: float) -> str:
        if self._error is not None:
            raise self._error
        return self._answer or ""


def _ask(client: TestClient) -> dict:
    session = client.post("/demo-sessions", json={"role": "advisor"})
    headers = {"Authorization": f"Bearer {session.json()['token']}"}
    return client.post("/contextual-chat", headers=headers, json=QUESTION).json()


def test_without_a_model_the_answer_is_the_grounded_fallback() -> None:
    """The public demo runs deterministically, so an answer still carries its citation."""
    body = _ask(TestClient(app))

    assert body["degraded"] is True
    assert body["citation_page"] == 18


def test_a_grounded_model_answer_is_returned_with_its_citation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    grounded = "TOYOTA-10K se alcanzo en el intervalo revisado."
    monkeypatch.setattr(main, "language_provider", StubProvider(answer=grounded))

    body = _ask(TestClient(app))

    assert body["degraded"] is False
    assert body["text"] == grounded
    assert body["citation_page"] == 18


def test_a_provider_outage_answers_200_not_500(monkeypatch: pytest.MonkeyPatch) -> None:
    """What if the model host is down while an Advisor is asking?"""
    monkeypatch.setattr(
        main, "language_provider", StubProvider(error=ProviderUnavailableError("down"))
    )
    client = TestClient(app)
    session = client.post("/demo-sessions", json={"role": "advisor"})

    response = client.post(
        "/contextual-chat",
        headers={"Authorization": f"Bearer {session.json()['token']}"},
        json=QUESTION,
    )

    assert response.status_code == 200
    assert response.json()["degraded"] is True
    assert "temporarily unavailable" in response.json()["text"]


def test_an_inventing_model_never_reaches_the_advisor(monkeypatch: pytest.MonkeyPatch) -> None:
    """What if the model answers with a price the recommendation never carried?"""
    monkeypatch.setattr(
        main,
        "language_provider",
        StubProvider(answer="TOYOTA-10K cuesta $4,500.00 MXN y es urgente."),
    )

    body = _ask(TestClient(app))

    assert body["degraded"] is True
    assert "4,500" not in body["text"]
