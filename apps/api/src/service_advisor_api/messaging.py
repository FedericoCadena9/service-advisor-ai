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
# An edited message may append whole approved clauses and nothing else. A word allowlist
# cannot hold: the words that spell the reschedule offer also spell a bare directive, and
# "necesita" plus "total" is already a claim about the price.
OPTIONAL_CLAUSES = (
    "Gracias por su preferencia.",
    "Si necesita cambiar la cita, responda a este mensaje.",
    "Su taller de confianza.",
    "Quedamos atentos.",
)
SERVICE_LABELS = {
    "HONDA-A1": "cambio de aceite y filtro",
    "HONDA-TIRE-ROTATION": "rotacion de llantas",
    "HONDA-CABIN-FILTER": "filtro de cabina",
    "HONDA-BRAKE-PADS-FRONT": "balatas delanteras",
    "HONDA-TURBO-COOLANT": "refrigerante turbo",
}
# Outside the approved facts and labels a message may only hold words and plain punctuation:
# a digit, symbol or emoji is how a second price, a phone number or urgency gets smuggled in.
_PRIORITY_LIST = re.compile(r"su servicio incluye ([^.]*)\.")


class InventedContentError(ValueError):
    """Raised when message text states anything the approved quote does not support."""


class MessageAlreadySentError(RuntimeError):
    """Raised when a quote already has a different message; the first text is authoritative."""


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
    """Accept the approved message, optionally shortened, plus whole approved clauses.

    Everything the customer reads is either a field the approval carries or a clause from
    OPTIONAL_CLAUSES. Nothing can be composed: once the approved parts are removed the
    remainder must be empty.
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

    remainder = text
    for fixed in (opening, f"Total {total}", total, f"Cita {slot_label}.", CONFIRMATION):
        remainder = remainder.replace(fixed, " ", 1)
    remainder = _strip_priorities(remainder, service_codes, text)
    for clause in OPTIONAL_CLAUSES:
        remainder = remainder.replace(clause, " ")

    leftover = remainder.strip(" ,.")
    if leftover:
        raise InventedContentError(
            f"Message adds {leftover.strip()!r}, which the approved quote does not support"
        )
    return segments


def _strip_priorities(remainder: str, service_codes: tuple[str, ...], text: str) -> str:
    """Remove the priority list, refusing any service the approval does not carry."""
    allowed_labels = [
        SERVICE_LABELS.get(service_code, service_code.lower()) for service_code in service_codes
    ]
    if sum(text.count(label) for label in allowed_labels) > MAX_PRIORITIES:
        raise InventedContentError(f"Message lists more than {MAX_PRIORITIES} priorities")

    match = _PRIORITY_LIST.search(remainder)
    if match is None:
        return remainder
    for listed in match.group(1).split(","):
        if listed.strip() not in allowed_labels:
            raise InventedContentError(
                f"Message names {listed.strip()!r}, which the approved quote does not contain"
            )
    return remainder.replace(match.group(0), " ", 1)


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
                if existing.text != text:
                    raise MessageAlreadySentError(
                        "This quote already has an approved message; redraft to change it"
                    )
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
