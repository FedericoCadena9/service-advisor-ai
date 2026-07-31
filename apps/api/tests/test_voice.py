from datetime import UTC, datetime

import pytest

from service_advisor_api.voice import (
    ConsentRequiredError,
    RecordingTooLongError,
    UnconfirmedTranscriptError,
    confirm,
    trace_payload,
    transcribe,
    workflow_transcript,
)

RECORDING = {
    "shop_id": "demo-shop",
    "demo_session_id": "session-1",
    "language": "es",
    "duration_seconds": 42.0,
    "consent": True,
    "provider_available": True,
}


def test_transcript_presents_language_timestamps_and_editable_text():
    note = transcribe(**RECORDING)

    assert note.language == "es"
    assert [segment.starts_at_seconds for segment in note.segments] == [0.0, 6.5]
    assert note.transcript.startswith("El cliente reporta un ruido al frenar")
    assert note.state == "transcribed"


def test_recording_beyond_ninety_seconds_is_refused():
    with pytest.raises(RecordingTooLongError):
        transcribe(**{**RECORDING, "duration_seconds": 90.1})


def test_recording_without_consent_is_refused():
    with pytest.raises(ConsentRequiredError):
        transcribe(**{**RECORDING, "consent": False})


def test_only_a_confirmed_transcript_reaches_the_workflow():
    note = transcribe(**RECORDING)

    with pytest.raises(UnconfirmedTranscriptError):
        workflow_transcript(note)
    corrected = confirm(note, "El cliente reporta un rechinido al frenar")
    assert workflow_transcript(corrected) == "El cliente reporta un rechinido al frenar"


def test_confirmed_audio_is_deleted():
    confirmed = confirm(transcribe(**RECORDING), "Ruido al frenar")

    assert confirmed.audio_retained is False
    assert confirmed.audio_retention_expires_at is None


def test_failed_transcription_keeps_audio_within_the_recovery_limit():
    note = transcribe(
        **{**RECORDING, "provider_available": False},
        now=datetime(2026, 7, 30, 12, 0, tzinfo=UTC),
    )

    assert note.state == "failed"
    assert note.manual_entry_available is True
    assert note.audio_retained is True
    assert note.audio_retention_expires_at == "2026-07-31T12:00:00+00:00"
    assert note.failure_reason == (
        "Transcription provider is unavailable; enter the concern manually"
    )


def test_traces_carry_no_audio_or_raw_transcript():
    payload = trace_payload(confirm(transcribe(**RECORDING), "Ruido al frenar"))

    assert payload["transcript_character_count"] == len("Ruido al frenar")
    assert "Ruido al frenar" not in str(payload)
    assert not any("audio_reference" in key for key in payload)
