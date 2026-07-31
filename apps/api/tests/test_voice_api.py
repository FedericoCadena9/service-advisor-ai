from fastapi.testclient import TestClient

from service_advisor_api.main import app

RECORDING = {"language": "es", "duration_seconds": 42.0, "consent": True}
CHECKIN = {
    "current_mileage_km": 48_000,
    "checked_in_on": "2026-07-27",
    "use_profile": "normal",
    "severe_use_factors": [],
    "appointment_window": "Tomorrow",
    "message_consent": True,
}


def _advisor_headers(client: TestClient) -> dict[str, str]:
    session = client.post("/demo-sessions", json={"role": "advisor"})
    return {"Authorization": f"Bearer {session.json()['token']}"}


def test_recording_returns_language_timestamps_and_an_editable_transcript() -> None:
    client = TestClient(app)

    response = client.post("/voice-notes", headers=_advisor_headers(client), json=RECORDING)

    body = response.json()
    assert response.status_code == 201
    assert body["language"] == "es"
    assert body["segments"][1]["starts_at_seconds"] == 6.5
    assert body["state"] == "transcribed"


def test_recording_over_the_limit_is_refused() -> None:
    client = TestClient(app)

    response = client.post(
        "/voice-notes",
        headers=_advisor_headers(client),
        json={**RECORDING, "duration_seconds": 120.0},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "A voice note may not exceed 90 seconds"


def test_recording_without_consent_is_refused() -> None:
    client = TestClient(app)

    response = client.post(
        "/voice-notes", headers=_advisor_headers(client), json={**RECORDING, "consent": False}
    )

    assert response.status_code == 422


def test_only_a_confirmed_transcript_reaches_the_check_in() -> None:
    client = TestClient(app)
    headers = _advisor_headers(client)
    note = client.post("/voice-notes", headers=headers, json=RECORDING).json()

    unconfirmed = client.post(
        "/vehicles/honda-civic-2019-lx/check-ins",
        headers=headers,
        json={**CHECKIN, "voice_note_id": note["id"]},
    )
    client.post(
        f"/voice-notes/{note['id']}/confirmation",
        headers=headers,
        json={"transcript": "Rechinido al frenar en bajada"},
    )
    confirmed = client.post(
        "/vehicles/honda-civic-2019-lx/check-ins",
        headers=headers,
        json={**CHECKIN, "voice_note_id": note["id"]},
    )

    assert unconfirmed.status_code == 409
    assert confirmed.status_code == 201
    assert confirmed.json()["concern"] == "Rechinido al frenar en bajada"


def test_confirmation_deletes_the_audio() -> None:
    client = TestClient(app)
    headers = _advisor_headers(client)
    note = client.post("/voice-notes", headers=headers, json=RECORDING).json()

    confirmed = client.post(
        f"/voice-notes/{note['id']}/confirmation",
        headers=headers,
        json={"transcript": "Rechinido al frenar"},
    ).json()

    assert confirmed["audio_retained"] is False
    assert confirmed["audio_retention_expires_at"] is None


def test_provider_failure_keeps_manual_entry_available() -> None:
    client = TestClient(app)
    headers = _advisor_headers(client)

    failed = client.post(
        "/voice-notes", headers=headers, json={**RECORDING, "provider_available": False}
    ).json()
    manual = client.post(
        "/vehicles/honda-civic-2019-lx/check-ins",
        headers=headers,
        json={**CHECKIN, "concern": "Ruido al frenar capturado a mano"},
    )

    assert failed["state"] == "failed"
    assert failed["manual_entry_available"] is True
    assert failed["audio_retention_expires_at"] is not None
    assert manual.status_code == 201
    assert manual.json()["concern"] == "Ruido al frenar capturado a mano"


def test_trace_contains_no_audio_or_raw_transcript() -> None:
    client = TestClient(app)
    headers = _advisor_headers(client)
    note = client.post("/voice-notes", headers=headers, json=RECORDING).json()
    client.post(
        f"/voice-notes/{note['id']}/confirmation",
        headers=headers,
        json={"transcript": "Rechinido al frenar en bajada"},
    )

    trace = client.get(f"/voice-notes/{note['id']}/trace", headers=headers)

    assert "Rechinido" not in trace.text
    assert "audio_reference" not in trace.text
    assert trace.json()["transcript_character_count"] == len("Rechinido al frenar en bajada")


def test_voice_note_is_scoped_to_the_demo_session() -> None:
    client = TestClient(app)
    note = client.post("/voice-notes", headers=_advisor_headers(client), json=RECORDING).json()

    response = client.get(f"/voice-notes/{note['id']}/trace", headers=_advisor_headers(client))

    assert response.status_code == 404
