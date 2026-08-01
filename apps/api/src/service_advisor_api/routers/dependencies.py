"""Dependencies shared by otherwise independent feature routers."""

from typing import Annotated

from fastapi import Header, HTTPException, status

from service_advisor_api import state
from service_advisor_api.auth import (
    ExpiredDemoSessionError,
    InvalidDemoSessionError,
    SessionClaims,
    verify_demo_session,
)
from service_advisor_api.voice import VoiceNote


def current_session(
    authorization: Annotated[str | None, Header()] = None,
) -> SessionClaims:
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Demo session is required")
    try:
        return verify_demo_session(authorization.removeprefix("Bearer "))
    except ExpiredDemoSessionError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error)) from error
    except InvalidDemoSessionError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid demo session") from error


def _require_manager(claims: SessionClaims) -> None:
    if claims.role not in ("manager", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Manager role is required")


def _load_voice_note(note_id: str, claims: SessionClaims) -> VoiceNote:
    try:
        return state.voice_note_store.get(
            note_id, shop_id=claims.shop_id, demo_session_id=claims.demo_session_id
        )
    except (KeyError, PermissionError) as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voice note not found") from error
