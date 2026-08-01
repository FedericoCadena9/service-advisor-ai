"""The demo's process-wide state, in one place.

Routers read these through the module (`state.language_provider`), never by importing the
value, so a test or a deployment can swap one without every router holding a stale copy.
"""

import os
from decimal import Decimal

from service_advisor_api.appointments import AppointmentStore
from service_advisor_api.approvals import QuoteCommandStore
from service_advisor_api.checkins import CheckinStore
from service_advisor_api.knowledge import KnowledgePack
from service_advisor_api.messaging import MessagingStore
from service_advisor_api.observability import TraceRecorder
from service_advisor_api.operations import OperationsStore
from service_advisor_api.overlays import OverlayStore
from service_advisor_api.providers import select_provider
from service_advisor_api.service_history import CivicServiceHistoryStore
from service_advisor_api.text_to_sql import SemanticQueryGateway
from service_advisor_api.vehicles import CanonicalVehicleStore
from service_advisor_api.voice import VoiceNoteStore
from service_advisor_api.workflows import AdvisorWorkflowStore

PROVIDER_CALL_COST_MXN = Decimal("0.0125")
SPAN_LATENCY_MS = 12.0

overlay_store = OverlayStore()
vehicle_store = CanonicalVehicleStore()
vehicle_store.seed()
checkin_store = CheckinStore()
knowledge_pack = KnowledgePack()
service_history_store = CivicServiceHistoryStore()
service_history_store.seed()
workflow_store = AdvisorWorkflowStore()
operations_store = OperationsStore()
operations_store.seed()
quote_command_store = QuoteCommandStore()
appointment_store = AppointmentStore()
messaging_store = MessagingStore()
semantic_gateway = SemanticQueryGateway()
semantic_gateway.seed()
voice_note_store = VoiceNoteStore()
language_provider = select_provider()
trace_recorder = TraceRecorder()

# The first request after a scale-to-zero cold start reports itself as waking.
served_first_request = False


def environment_flag(name: str, *, default: bool) -> bool:
    """Read a deployment switch. Gate outcomes come from here, never from a caller."""
    raw = os.environ.get(name)
    return default if raw is None else raw.strip().lower() in ("1", "true", "yes")


def record_span(
    trace_id: str | None,
    *,
    name: str,
    kind: str,
    cost_mxn: Decimal = Decimal("0.0000"),
    attributes: dict[str, object] | None = None,
) -> None:
    """Emit one correlated span; prohibited fields are dropped inside the recorder."""
    if not trace_id:
        return
    trace_recorder.record(
        trace_id,
        name=name,
        kind=kind,
        latency_ms=SPAN_LATENCY_MS,
        cost_mxn=cost_mxn,
        attributes=attributes or {},
    )
