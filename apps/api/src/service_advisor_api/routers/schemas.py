"""HTTP request and response contracts shared by the feature routers."""

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

from service_advisor_api.auth import Role
from service_advisor_api.checkins import UseProfile
from service_advisor_api.voice import Language


class HealthResponse(BaseModel):
    status: Literal["healthy"]


class ReleaseManifestResponse(BaseModel):
    release_version: str
    model_version: str
    prompt_version: str
    dataset_version: str
    rule_versions: list[str]


class GateResultResponse(BaseModel):
    name: str
    passed: bool
    detail: str


class ReadinessResponse(BaseModel):
    status: Literal["ready", "waking"]
    cold_start: bool
    manifest: ReleaseManifestResponse
    gates: list[GateResultResponse]
    migration_steps: list[str]


class CreateDemoSessionRequest(BaseModel):
    role: Role


class DemoSessionResponse(BaseModel):
    token: str
    role: Role
    expires_at: str


class WorkspaceResponse(BaseModel):
    shop_id: str
    demo_session_id: str
    role: Role
    generation: int


class VehicleSearchResponse(BaseModel):
    id: str
    customer_label: str
    vehicle_label: str
    is_demo_data: bool


class VehicleSummaryResponse(BaseModel):
    id: str
    customer_label: str
    year: int
    make: str
    model: str
    trim: str
    engine: str
    drivetrain: str
    market: str
    prior_mileage_km: int
    prior_mileage_recorded_on: str
    is_demo_data: bool


class CheckinRequest(BaseModel):
    current_mileage_km: int
    checked_in_on: str
    use_profile: UseProfile
    severe_use_factors: list[str]
    concern: str = ""
    appointment_window: str
    message_consent: bool
    voice_note_id: str | None = None


class CheckinResponse(BaseModel):
    current_mileage_km: int
    prior_mileage_km: int
    checked_in_on: str
    use_profile: UseProfile
    severe_use_factors: list[str]
    concern: str
    appointment_window: str
    message_consent: bool


class ServiceRecordResponse(BaseModel):
    id: str
    service_code: str
    status: str


class ServiceHistoryResponse(BaseModel):
    completed: list[ServiceRecordResponse]
    declined: list[ServiceRecordResponse]


class RecommendationResponse(BaseModel):
    state: str
    actionable: bool
    service_code: str | None
    rule_version: str | None
    due_reason: str
    citation_page: int | None
    citation_section: str | None
    confidence: str
    warnings: list[str]
    declined_service_ids: list[str]


class AdvisorRunResponse(BaseModel):
    id: str
    events: list[str]
    decision: str | None
    command_executed: bool
    trace_id: str


class AdvisorDecisionRequest(BaseModel):
    decision: Literal["approve", "reject"]


class ExplanationRequest(BaseModel):
    vehicle_id: str
    current_mileage_km: int
    evidence_available: bool


class ExplanationResponse(BaseModel):
    text: str
    citation_page: int | None
    citation_section: str | None
    degraded: bool


class ChatRequest(BaseModel):
    question: str
    vehicle_id: str
    current_mileage_km: int


class QuoteDraftRequest(BaseModel):
    service_codes: list[str]


class QuoteLineResponse(BaseModel):
    service_code: str
    labor_mxn: Decimal
    parts_mxn: Decimal
    iva_mxn: Decimal
    total_mxn: Decimal
    duration_minutes: int
    fitment: str
    available: bool
    unavailable_reason: str | None


class QuoteDraftResponse(BaseModel):
    lines: list[QuoteLineResponse]
    subtotal_mxn: Decimal
    iva_mxn: Decimal
    total_mxn: Decimal
    duration_minutes: int
    bay_slot_id: str | None
    warnings: list[str]


class QuoteFactsResponse(BaseModel):
    service_codes: list[str]
    subtotal_mxn: Decimal
    iva_mxn: Decimal
    total_mxn: Decimal
    duration_minutes: int
    bay_slot_id: str | None


class QuoteCitationsResponse(BaseModel):
    rule_version: str | None
    citation_page: int | None
    citation_section: str | None


class QuoteReviewResponse(BaseModel):
    id: str
    vehicle_id: str
    approver_role: Role
    approver_session_id: str
    facts: QuoteFactsResponse
    citations: QuoteCitationsResponse
    status: str
    expires_at: str
    invalidation_reason: str | None
    escalation_required: bool
    escalation_reasons: list[str]
    evidence_blocked: bool
    blocking_reason: str | None


class QuoteDecisionRequest(BaseModel):
    decision: Literal["approve", "reject"]
    idempotency_key: str
    reason: str | None = None


class QuoteDecisionResponse(BaseModel):
    id: str
    review_id: str
    quote_id: str | None
    decision: str
    approver_role: str
    approver_session_id: str
    reason: str | None
    facts: QuoteFactsResponse
    citations: QuoteCitationsResponse
    escalation_reasons: list[str]


class AppointmentResponse(BaseModel):
    id: str
    quote_id: str
    bay_slot_id: str
    starts_at: str
    approver_role: str
    simulated: bool


class SmsPreviewResponse(BaseModel):
    text: str
    segments: int
    priorities: list[str]


class SmsRequest(BaseModel):
    text: str


class SmsDeliveryResponse(BaseModel):
    id: str
    quote_id: str
    text: str
    segments: int
    state: str
    simulated: bool
    approver_role: str
    rule_version: str | None
    citation_page: int | None
    citation_section: str | None


class VoiceNoteRequest(BaseModel):
    language: Language
    duration_seconds: float
    consent: bool
    provider_available: bool = True


class TranscriptSegmentResponse(BaseModel):
    starts_at_seconds: float
    text: str


class VoiceNoteResponse(BaseModel):
    id: str
    language: Language
    duration_seconds: float
    state: str
    segments: list[TranscriptSegmentResponse]
    transcript: str
    audio_retained: bool
    audio_retention_expires_at: str | None
    failure_reason: str | None
    manual_entry_available: bool


class ConfirmTranscriptRequest(BaseModel):
    transcript: str


class EvaluationReportResponse(BaseModel):
    case_count: int
    scores: dict[str, float]
    thresholds_met: bool
    kinds: dict[str, int]
    dataset_version: str
    prompt_version: str
    provider: str
    rule_versions: list[str]
    failing_case_ids: list[str]


class SpanResponse(BaseModel):
    span_id: str
    parent_span_id: str | None
    name: str
    kind: str
    latency_ms: float
    cost_mxn: str
    attributes: dict[str, object]


class TraceVersionsResponse(BaseModel):
    rule_version: str | None
    prompt_version: str
    dataset_version: str
    model: str


class TraceResponse(BaseModel):
    trace_id: str
    versions: TraceVersionsResponse
    spans: list[SpanResponse]


class DashboardResponse(BaseModel):
    trace_count: int
    span_count: int
    spans_by_kind: dict[str, int]
    citation_rate: float
    p50_latency_ms: float
    p95_latency_ms: float
    total_cost_mxn: str
    escalation_outcomes: dict[str, int]
    evaluation_thresholds_met: bool
    evaluation_score: float


class VoiceTraceResponse(BaseModel):
    voice_note_id: str
    language: Language
    duration_seconds: float
    state: str
    segment_count: int
    transcript_character_count: int
    audio_retained: bool


class ServiceQuestionRequest(BaseModel):
    question: str


class RetrievalMetadataResponse(BaseModel):
    views: list[str]
    columns: list[str]
    row_limit: int
    timeout_seconds: float
    principal: str


class ServiceQuestionResponse(BaseModel):
    answer: str
    sql: str
    rows: list[list[str]]
    retrieval: RetrievalMetadataResponse
