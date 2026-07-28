import base64
import hashlib
import hmac
import json
import os
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel

Role = Literal["advisor", "manager", "admin"]
SESSION_TTL = timedelta(minutes=30)
SHOP_ID = "demo-shop"


class InvalidDemoSessionError(ValueError):
    """Raised when a demo-session token cannot be trusted."""


class ExpiredDemoSessionError(InvalidDemoSessionError):
    """Raised when a signed demo session is no longer valid."""


class SessionClaims(BaseModel):
    role: Role
    shop_id: str
    demo_session_id: str
    expires_at: datetime


def create_demo_session(role: Role, *, now: datetime | None = None) -> str:
    issued_at = now or datetime.now(UTC)
    expires_at = issued_at + SESSION_TTL
    payload = {
        "role": role,
        "shop_id": SHOP_ID,
        "demo_session_id": str(uuid4()),
        "expires_at": expires_at.isoformat(),
    }
    encoded_payload = _encode(json.dumps(payload, separators=(",", ":")).encode())
    signature = _sign(encoded_payload)
    return f"{encoded_payload}.{signature}"


def verify_demo_session(token: str, *, now: datetime | None = None) -> SessionClaims:
    try:
        encoded_payload, signature = token.split(".")
    except ValueError as error:
        raise InvalidDemoSessionError("Malformed demo session") from error

    if not hmac.compare_digest(_sign(encoded_payload), signature):
        raise InvalidDemoSessionError("Invalid demo session signature")

    try:
        claims = SessionClaims.model_validate_json(_decode(encoded_payload))
    except (ValueError, json.JSONDecodeError) as error:
        raise InvalidDemoSessionError("Invalid demo session payload") from error

    current_time = now or datetime.now(UTC)
    if claims.expires_at <= current_time:
        raise ExpiredDemoSessionError("Demo session has expired")

    return claims


def _secret() -> bytes:
    return os.environ.get("DEMO_SESSION_SECRET", "local-demo-session-secret").encode()


def _sign(encoded_payload: str) -> str:
    return hmac.new(_secret(), encoded_payload.encode(), hashlib.sha256).hexdigest()


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def _decode(value: str) -> str:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
