"""Voice-note transcription, confirmation, and trace endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from service_advisor_api import state
from service_advisor_api.auth import SessionClaims
from service_advisor_api.routers.dependencies import _load_voice_note, current_session
from service_advisor_api.routers.schemas import (
    ConfirmTranscriptRequest,
    TranscriptSegmentResponse,
    VoiceNoteRequest,
    VoiceNoteResponse,
    VoiceTraceResponse,
)
from service_advisor_api.voice import (
    ConsentRequiredError,
    RecordingTooLongError,
    UnconfirmedTranscriptError,
    VoiceNote,
    confirm,
    trace_payload,
    transcribe,
)

router = APIRouter()


def _voice_response(note: VoiceNote) -> VoiceNoteResponse:
    return VoiceNoteResponse(
        id=note.id,
        language=note.language,
        duration_seconds=note.duration_seconds,
        state=note.state,
        segments=[
            TranscriptSegmentResponse(starts_at_seconds=segment.starts_at_seconds, text=segment.text)
            for segment in note.segments
        ],
        transcript=note.transcript,
        audio_retained=note.audio_retained,
        audio_retention_expires_at=note.audio_retention_expires_at,
        failure_reason=note.failure_reason,
        manual_entry_available=note.manual_entry_available,
    )


@router.post("/voice-notes", response_model=VoiceNoteResponse, status_code=status.HTTP_201_CREATED)
def create_voice_note(
    request: VoiceNoteRequest, claims: Annotated[SessionClaims, Depends(current_session)]
) -> VoiceNoteResponse:
    try:
        note = transcribe(
            shop_id=claims.shop_id,
            demo_session_id=claims.demo_session_id,
            language=request.language,
            duration_seconds=request.duration_seconds,
            consent=request.consent,
            provider_available=request.provider_available,
        )
    except (RecordingTooLongError, ConsentRequiredError) as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    return _voice_response(state.voice_note_store.save(note))


@router.post("/voice-notes/{note_id}/confirmation", response_model=VoiceNoteResponse)
def confirm_voice_note(
    note_id: str,
    request: ConfirmTranscriptRequest,
    claims: Annotated[SessionClaims, Depends(current_session)],
) -> VoiceNoteResponse:
    note = _load_voice_note(note_id, claims)
    try:
        confirmed = confirm(note, request.transcript)
    except UnconfirmedTranscriptError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    return _voice_response(state.voice_note_store.save(confirmed))


@router.get("/voice-notes/{note_id}/trace", response_model=VoiceTraceResponse)
def get_voice_trace(
    note_id: str, claims: Annotated[SessionClaims, Depends(current_session)]
) -> VoiceTraceResponse:
    return VoiceTraceResponse.model_validate(trace_payload(_load_voice_note(note_id, claims)))
