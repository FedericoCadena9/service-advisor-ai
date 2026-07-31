from dataclasses import dataclass
from uuid import UUID, uuid5

# Fixed namespace so a reservation id is reproducible from its approved quote.
APPOINTMENT_NAMESPACE = UUID("2f9d5a3e-8b6c-4d5e-9f10-7a1c3b5d9e02")


class UnapprovedQuoteError(RuntimeError):
    """Raised when a reservation is attempted without a valid human approval."""


@dataclass(frozen=True)
class Appointment:
    id: str
    quote_id: str
    shop_id: str
    demo_session_id: str
    bay_slot_id: str
    starts_at: str
    approver_role: str
    simulated: bool = True


class AppointmentStore:
    """Deterministic, idempotent reservations of simulated bay-capacity slots."""

    def __init__(self) -> None:
        self._appointments: dict[str, Appointment] = {}

    def reserve(
        self,
        *,
        quote_id: str,
        shop_id: str,
        demo_session_id: str,
        bay_slot_id: str,
        starts_at: str,
        approver_role: str,
    ) -> Appointment:
        appointment_id = str(uuid5(APPOINTMENT_NAMESPACE, f"appointment:{quote_id}"))
        existing = self._appointments.get(appointment_id)
        if existing is not None:
            return existing
        appointment = Appointment(
            id=appointment_id,
            quote_id=quote_id,
            shop_id=shop_id,
            demo_session_id=demo_session_id,
            bay_slot_id=bay_slot_id,
            starts_at=starts_at,
            approver_role=approver_role,
        )
        self._appointments[appointment_id] = appointment
        return appointment

    def for_quote(self, quote_id: str, shop_id: str, demo_session_id: str) -> Appointment | None:
        appointment = self._appointments.get(
            str(uuid5(APPOINTMENT_NAMESPACE, f"appointment:{quote_id}"))
        )
        if appointment is None:
            return None
        if (appointment.shop_id, appointment.demo_session_id) != (shop_id, demo_session_id):
            raise PermissionError("Appointment is outside this demo session")
        return appointment
