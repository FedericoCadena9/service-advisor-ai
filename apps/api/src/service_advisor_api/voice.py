from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from threading import RLock
from typing import Literal
from uuid import uuid4

MAX_DURATION_SECONDS = 90
FAILED_AUDIO_RETENTION = timedelta(hours=24)
Language = Literal["en", "es"]
DRAFT_SEGMENTS: dict[str, tuple[tuple[float, str], ...]] = {
    "es": (
        (0.0, "El cliente reporta un ruido al frenar"),
        (6.5, "Pide revision antes del viaje del viernes"),
    ),
    "en": (
        (0.0, "The customer reports a noise when braking"),
        (6.5, "They want it checked before Friday"),
    ),
}


class RecordingTooLongError(ValueError):
    """Raised when a voice note exceeds the agreed 90 second limit."""


class ConsentRequiredError(ValueError):
    """Raised when a voice note is recorded without recording consent."""


class UnconfirmedTranscriptError(RuntimeError):
    """Raised when an unconfirmed transcript is pushed into an Advisor Run."""


@dataclass(frozen=True)
class TranscriptSegment:
    starts_at_seconds: float
    text: str


@dataclass(frozen=True)
class VoiceNote:
    id: str
    shop_id: str
    demo_session_id: str
    language: Language
    duration_seconds: float
    state: str
    segments: tuple[TranscriptSegment, ...]
    transcript: str
    audio_retained: bool
    audio_retention_expires_at: str | None
    failure_reason: str | None
    manual_entry_available: bool


def transcribe(
    *,
    shop_id: str,
    demo_session_id: str,
    language: Language,
    duration_seconds: float,
    consent: bool,
    provider_available: bool,
    now: datetime | None = None,
) -> VoiceNote:
    """Produce an editable transcript, or a failed note that keeps audio for recovery only."""
    if duration_seconds > MAX_DURATION_SECONDS:
        raise RecordingTooLongError(
            f"A voice note may not exceed {MAX_DURATION_SECONDS} seconds"
        )
    if not consent:
        raise ConsentRequiredError("Recording consent is required before transcription")

    common = {
        "id": str(uuid4()),
        "shop_id": shop_id,
        "demo_session_id": demo_session_id,
        "language": language,
        "duration_seconds": duration_seconds,
    }
    if not provider_available:
        expires_at = (now or datetime.now(UTC)) + FAILED_AUDIO_RETENTION
        return VoiceNote(
            **common,
            state="failed",
            segments=(),
            transcript="",
            audio_retained=True,
            audio_retention_expires_at=expires_at.isoformat(),
            failure_reason="Transcription provider is unavailable; enter the concern manually",
            manual_entry_available=True,
        )
    segments = tuple(
        TranscriptSegment(starts_at_seconds=offset, text=text)
        for offset, text in DRAFT_SEGMENTS[language]
    )
    # Audio kept only until the Advisor confirms, and never past the recovery limit.
    expires_at = (now or datetime.now(UTC)) + FAILED_AUDIO_RETENTION
    return VoiceNote(
        **common,
        state="transcribed",
        segments=segments,
        transcript=". ".join(segment.text for segment in segments),
        audio_retained=True,
        audio_retention_expires_at=expires_at.isoformat(),
        failure_reason=None,
        manual_entry_available=True,
    )


def confirm(note: VoiceNote, transcript: str) -> VoiceNote:
    """Confirm a corrected transcript and delete the audio it came from."""
    if not transcript.strip():
        raise UnconfirmedTranscriptError("A confirmed transcript cannot be empty")
    return replace(
        note,
        state="confirmed",
        transcript=transcript.strip(),
        audio_retained=False,
        audio_retention_expires_at=None,
    )


def workflow_transcript(note: VoiceNote) -> str:
    if note.state != "confirmed":
        raise UnconfirmedTranscriptError("Only a confirmed transcript can reach an Advisor Run")
    return note.transcript


def trace_payload(note: VoiceNote) -> dict[str, object]:
    """Observability keeps shape, never audio or raw transcript content."""
    return {
        "voice_note_id": note.id,
        "language": note.language,
        "duration_seconds": note.duration_seconds,
        "state": note.state,
        "segment_count": len(note.segments),
        "transcript_character_count": len(note.transcript),
        "audio_retained": note.audio_retained,
    }


class VoiceNoteStore:
    def __init__(self) -> None:
        self._lock = RLock()
        self._notes: dict[str, VoiceNote] = {}

    def save(self, note: VoiceNote) -> VoiceNote:
        with self._lock:
            self._notes[note.id] = note
        return note

    def get(self, note_id: str, *, shop_id: str, demo_session_id: str) -> VoiceNote:
        with self._lock:
            note = self._notes[note_id]
        if (note.shop_id, note.demo_session_id) != (shop_id, demo_session_id):
            raise PermissionError("Voice note is outside this demo session")
        return note
