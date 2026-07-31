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
FORBIDDEN_URGENCY = ("urgente", "peligro", "inseguro", "falla grave")
SERVICE_LABELS = {
    "HONDA-A1": "cambio de aceite y filtro",
    "HONDA-TIRE-ROTATION": "rotacion de llantas",
    "HONDA-CABIN-FILTER": "filtro de cabina",
    "HONDA-BRAKE-PADS-FRONT": "balatas delanteras",
    "HONDA-TURBO-COOLANT": "refrigerante turbo",
}
_AMOUNT = re.compile(r"\$?\s?([\d,]+\.\d{2})")
_SERVICE_TOKEN = re.compile(r"\b[A-Z][A-Z0-9]+(?:-[A-Z0-9]+)+\b")
_SLOT_TOKEN = re.compile(r"\bbay-[a-z0-9-]+\b")


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
    """Reject edited text that invents recipient, price, service, slot, or urgency."""
    segments = _segments(text)
    if segments > MAX_SEGMENTS:
        raise MessageTooLongError(f"Message uses {segments} segments; the limit is {MAX_SEGMENTS}")
    if not text.startswith(f"Hola {customer_label}"):
        raise InventedContentError("Message must address the approved recipient")
    for amount in _AMOUNT.findall(text):
        if Decimal(amount.replace(",", "")) != total_mxn:
            raise InventedContentError("Message states a price the approved quote does not contain")
    for token in _SERVICE_TOKEN.findall(text):
        if token not in service_codes:
            raise InventedContentError("Message names a service the approved quote does not contain")
    if slot_label not in text:
        raise InventedContentError("Message must state the approved appointment slot")
    for slot in _SLOT_TOKEN.findall(text):
        if slot != slot_label:
            raise InventedContentError("Message names a slot the approved quote does not contain")
    labels = [label for label in SERVICE_LABELS.values() if label in text.lower()]
    if len(labels) > MAX_PRIORITIES:
        raise InventedContentError(f"Message lists more than {MAX_PRIORITIES} priorities")
    if any(word in text.lower() for word in FORBIDDEN_URGENCY):
        raise InventedContentError("Message invents urgency the recommendation does not support")
    if "¿confirma" not in text.lower():
        raise InventedContentError("Message must ask the customer to confirm")
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
