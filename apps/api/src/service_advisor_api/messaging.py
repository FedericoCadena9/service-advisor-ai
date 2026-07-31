import re
from dataclasses import dataclass, replace
from decimal import Decimal
from math import ceil
from threading import RLock
from typing import ClassVar
from uuid import uuid5

from service_advisor_api.appointments import APPOINTMENT_NAMESPACE

SEGMENT_LENGTH = 160
MAX_SEGMENTS = 3
MAX_PRIORITIES = 3
CONFIRMATION = "¿Confirma la cita?"
# Everything an edited message may say beyond the approved facts and service labels.
CONNECTIVE_VOCABULARY = frozenset(
    {"su", "servicio", "incluye", "y", "e", "total", "cita", "gracias", "por", "favor"}
)
SERVICE_LABELS = {
    "HONDA-A1": "cambio de aceite y filtro",
    "HONDA-TIRE-ROTATION": "rotacion de llantas",
    "HONDA-CABIN-FILTER": "filtro de cabina",
    "HONDA-BRAKE-PADS-FRONT": "balatas delanteras",
    "HONDA-TURBO-COOLANT": "refrigerante turbo",
}
_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)


class InventedContentError(ValueError):
    """Raised when message text states anything the approved quote does not support."""


class MessageTooLongError(ValueError):
    """Raised when message text exceeds the agreed three-segment limit."""


@dataclass(frozen=True)
class SmsPreview:
    text: str
    segments: int
    priorities: tuple[str, ...]


@dataclass(frozen=True)
class SmsDelivery:
    id: str
    quote_id: str
    shop_id: str
    demo_session_id: str
    text: str
    segments: int
    state: str
    simulated: bool
    approver_role: str
    rule_version: str | None
    citation_page: int | None
    citation_section: str | None


def compose_sms(
    *,
    customer_label: str,
    service_codes: tuple[str, ...],
    total_mxn: Decimal,
    slot_label: str,
) -> SmsPreview:
    """Build the preview only from approved structured fields."""
    priorities = tuple(
        SERVICE_LABELS.get(service_code, service_code.lower())
        for service_code in service_codes[:MAX_PRIORITIES]
    )
    text = (
        f"Hola {customer_label}: su servicio incluye {', '.join(priorities)}. "
        f"Total ${total_mxn:,.2f} MXN con IVA incluido. Cita {slot_label}. "
        "¿Confirma la cita?"
    )
    return SmsPreview(text=text, segments=_segments(text), priorities=priorities)


def validate_sms(
    text: str,
    *,
    customer_label: str,
    service_codes: tuple[str, ...],
    total_mxn: Decimal,
    slot_label: str,
) -> int:
    """Accept only wording the approved quote supports.

    The check is an allowlist, not a denylist: the message must open with the approved
    recipient, state the approved total and slot, ask for confirmation, and use no words
    beyond the approved service labels and a small connective vocabulary. Anything invented
    -- a second recipient, a price in words, an unquoted service, urgency -- has no way in.
    """
    segments = _segments(text)
    if segments > MAX_SEGMENTS:
        raise MessageTooLongError(f"Message uses {segments} segments; the limit is {MAX_SEGMENTS}")

    total = f"${total_mxn:,.2f} MXN con IVA incluido."
    opening = f"Hola {customer_label}:"
    if not text.startswith(opening):
        raise InventedContentError("Message must address the approved recipient")
    if total not in text:
        raise InventedContentError("Message states a price the approved quote does not contain")
    if f"Cita {slot_label}." not in text:
        raise InventedContentError("Message must state the approved appointment slot")
    if CONFIRMATION not in text:
        raise InventedContentError("Message must ask the customer to confirm")

    allowed_labels = [
        SERVICE_LABELS.get(service_code, service_code.lower()) for service_code in service_codes
    ]
    remainder = text
    for fixed in (opening, total, f"Cita {slot_label}.", CONFIRMATION):
        remainder = remainder.replace(fixed, " ", 1)
    for label in allowed_labels:
        remainder = remainder.replace(label, " ")

    quoted_priorities = sum(1 for label in allowed_labels if label in text)
    if quoted_priorities > MAX_PRIORITIES:
        raise InventedContentError(f"Message lists more than {MAX_PRIORITIES} priorities")

    for word in _WORD.findall(remainder.lower()):
        if word not in CONNECTIVE_VOCABULARY:
            raise InventedContentError(
                f"Message says {word!r}, which the approved quote does not support"
            )
    return segments


class MessagingStore:
    """Simulated SMS delivery: nothing leaves the demo environment."""

    NEXT_STATE: ClassVar[dict[str, str]] = {
        "queued": "sent",
        "sent": "delivered",
        "delivered": "delivered",
    }

    def __init__(self) -> None:
        self._lock = RLock()
        self._deliveries: dict[str, SmsDelivery] = {}

    def enqueue(
        self,
        *,
        quote_id: str,
        shop_id: str,
        demo_session_id: str,
        text: str,
        segments: int,
        approver_role: str,
        rule_version: str | None,
        citation_page: int | None,
        citation_section: str | None,
    ) -> SmsDelivery:
        delivery_id = str(uuid5(APPOINTMENT_NAMESPACE, f"sms:{quote_id}"))
        with self._lock:
            existing = self._deliveries.get(delivery_id)
            if existing is not None:
                return existing
            delivery = SmsDelivery(
                id=delivery_id,
                quote_id=quote_id,
                shop_id=shop_id,
                demo_session_id=demo_session_id,
                text=text,
                segments=segments,
                state="queued",
                simulated=True,
                approver_role=approver_role,
                rule_version=rule_version,
                citation_page=citation_page,
                citation_section=citation_section,
            )
            self._deliveries[delivery_id] = delivery
            return delivery

    def get(self, delivery_id: str, *, shop_id: str, demo_session_id: str) -> SmsDelivery:
        with self._lock:
            delivery = self._deliveries[delivery_id]
        if (delivery.shop_id, delivery.demo_session_id) != (shop_id, demo_session_id):
            raise PermissionError("Message is outside this demo session")
        return delivery

    def advance(self, delivery_id: str, *, shop_id: str, demo_session_id: str) -> SmsDelivery:
        with self._lock:
            delivery = self.get(
                delivery_id, shop_id=shop_id, demo_session_id=demo_session_id
            )
            advanced = replace(delivery, state=self.NEXT_STATE[delivery.state])
            self._deliveries[delivery_id] = advanced
            return advanced



def _segments(text: str) -> int:
    return max(1, ceil(len(text) / SEGMENT_LENGTH))
