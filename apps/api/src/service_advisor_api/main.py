from decimal import Decimal
from typing import Annotated, Literal, NamedTuple

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from service_advisor_api.appointments import Appointment, AppointmentStore
from service_advisor_api.approvals import (
    QuoteCitations,
    QuoteCommandStore,
    QuoteDecision,
    QuoteFacts,
    QuoteReview,
    StaleQuoteError,
)
from service_advisor_api.auth import (
    ExpiredDemoSessionError,
    InvalidDemoSessionError,
    Role,
    SessionClaims,
    create_demo_session,
    verify_demo_session,
)
from service_advisor_api.chat import answer_contextual_question
from service_advisor_api.checkins import (
    Checkin,
    CheckinStore,
    InvalidCheckinError,
    UseProfile,
    validate_checkin,
)
from service_advisor_api.escalation import (
    EscalationAssessment,
    EscalationReasonRequiredError,
    EscalationRequiredError,
    EvidenceInsufficientError,
    assess_escalation,
)
from service_advisor_api.evaluation import run_suite
from service_advisor_api.explanations import explain_recommendation
from service_advisor_api.knowledge import KnowledgePack
from service_advisor_api.messaging import (
    InventedContentError,
    MessageTooLongError,
    MessagingStore,
    SmsDelivery,
    compose_sms,
    validate_sms,
)
from service_advisor_api.operations import OperationsStore
from service_advisor_api.overlays import DemoOverlay, OverlayStore
from service_advisor_api.quotes import (
    InformationalServiceError,
    QuoteDraft,
    UnknownServiceError,
    draft_quote,
    fingerprint,
    required_part_numbers,
)
from service_advisor_api.recommendations import (
    Recommendation,
    evaluate_civic_maintenance,
    evaluate_maintenance,
)
from service_advisor_api.service_history import CivicServiceHistoryStore, ServiceRecord
from service_advisor_api.text_to_sql import (
    QueryTimeoutError,
    SemanticQueryGateway,
    UnsafeSqlError,
    UnsupportedQuestionError,
)
from service_advisor_api.vehicles import (
    CanonicalVehicle,
    CanonicalVehicleStore,
    VehicleSearchResult,
)
from service_advisor_api.voice import (
    ConsentRequiredError,
    Language,
    RecordingTooLongError,
    UnconfirmedTranscriptError,
    VoiceNote,
    VoiceNoteStore,
    confirm,
    trace_payload,
    transcribe,
    workflow_transcript,
)
from service_advisor_api.workflows import AdvisorRun, AdvisorWorkflowStore


class HealthResponse(BaseModel):
    status: Literal["healthy"]


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


class AdvisorDecisionRequest(BaseModel):
    decision: Literal["approve", "reject"]


class ExplanationRequest(BaseModel):
    current_mileage_km: int
    evidence_available: bool


class ExplanationResponse(BaseModel):
    text: str
    citation_page: int | None
    citation_section: str | None
    degraded: bool


class ChatRequest(BaseModel):
    question: str
    current_mileage_km: int
    provider_available: bool


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


app = FastAPI(title="Service Advisor API", version="0.1.0")
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:4173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    return HealthResponse(status="healthy")


@app.post("/demo-sessions", response_model=DemoSessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(request: CreateDemoSessionRequest) -> DemoSessionResponse:
    token = create_demo_session(request.role)
    claims = verify_demo_session(token)
    return DemoSessionResponse(
        token=token,
        role=claims.role,
        expires_at=claims.expires_at.isoformat(),
    )


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


def _workspace_response(claims: SessionClaims, overlay: DemoOverlay) -> WorkspaceResponse:
    return WorkspaceResponse(
        shop_id=claims.shop_id,
        demo_session_id=claims.demo_session_id,
        role=claims.role,
        generation=overlay.generation,
    )


@app.get("/workspace", response_model=WorkspaceResponse)
def get_workspace(claims: Annotated[SessionClaims, Depends(current_session)]) -> WorkspaceResponse:
    overlay = overlay_store.get_or_create(
        shop_id=claims.shop_id,
        demo_session_id=claims.demo_session_id,
        role=claims.role,
    )
    return _workspace_response(claims, overlay)


@app.post("/workspace/reset", response_model=WorkspaceResponse)
def reset_workspace(claims: Annotated[SessionClaims, Depends(current_session)]) -> WorkspaceResponse:
    overlay = overlay_store.reset(
        shop_id=claims.shop_id,
        demo_session_id=claims.demo_session_id,
        role=claims.role,
    )
    return _workspace_response(claims, overlay)


@app.get("/admin/demo-sessions", response_model=list[WorkspaceResponse])
def list_demo_sessions(
    claims: Annotated[SessionClaims, Depends(current_session)],
) -> list[WorkspaceResponse]:
    if claims.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role is required")
    return [
        WorkspaceResponse(
            shop_id=overlay.shop_id,
            demo_session_id=overlay.demo_session_id,
            role=overlay.role,
            generation=overlay.generation,
        )
        for overlay in overlay_store.list_for_shop(claims.shop_id)
    ]


@app.get("/admin/knowledge/civic-rule")
def inspect_civic_rule(claims: Annotated[SessionClaims, Depends(current_session)]) -> dict[str, dict[str, object]]:
    if claims.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role is required")
    return knowledge_pack.inspection()


@app.get("/vehicles/search", response_model=list[VehicleSearchResponse])
def search_vehicles(
    query: Annotated[str, Query(min_length=1)],
    claims: Annotated[SessionClaims, Depends(current_session)],
) -> list[VehicleSearchResult]:
    return vehicle_store.search(shop_id=claims.shop_id, query=query)


@app.get("/vehicles/{vehicle_id}", response_model=VehicleSummaryResponse)
def get_vehicle(
    vehicle_id: str,
    claims: Annotated[SessionClaims, Depends(current_session)],
) -> VehicleSummaryResponse:
    vehicle = vehicle_store.get(shop_id=claims.shop_id, vehicle_id=vehicle_id)
    if vehicle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    return VehicleSummaryResponse.model_validate(vehicle, from_attributes=True)


def _service_record_response(record: ServiceRecord) -> ServiceRecordResponse:
    return ServiceRecordResponse(id=record.id, service_code=record.service_code, status=record.status)


@app.get("/vehicles/{vehicle_id}/history", response_model=ServiceHistoryResponse)
def get_service_history(
    vehicle_id: str,
    claims: Annotated[SessionClaims, Depends(current_session)],
) -> ServiceHistoryResponse:
    return ServiceHistoryResponse(
        completed=[
            _service_record_response(record)
            for record in service_history_store.completed(claims.shop_id, vehicle_id)
        ],
        declined=[
            _service_record_response(record)
            for record in service_history_store.declined(claims.shop_id, vehicle_id)
        ],
    )


def _checkin_response(checkin: Checkin) -> CheckinResponse:
    return CheckinResponse(
        current_mileage_km=checkin.current_mileage_km,
        prior_mileage_km=checkin.prior_mileage_km,
        checked_in_on=checkin.checked_in_on,
        use_profile=checkin.use_profile,
        severe_use_factors=list(checkin.severe_use_factors),
        concern=checkin.concern,
        appointment_window=checkin.appointment_window,
        message_consent=checkin.message_consent,
    )


@app.post(
    "/vehicles/{vehicle_id}/check-ins",
    response_model=CheckinResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_checkin(
    vehicle_id: str,
    request: CheckinRequest,
    claims: Annotated[SessionClaims, Depends(current_session)],
) -> CheckinResponse:
    vehicle = vehicle_store.get(shop_id=claims.shop_id, vehicle_id=vehicle_id)
    if vehicle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    fields = request.model_dump(exclude={"voice_note_id"})
    if request.voice_note_id is not None:
        try:
            fields["concern"] = workflow_transcript(_load_voice_note(request.voice_note_id, claims))
        except UnconfirmedTranscriptError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=str(error)
            ) from error
    try:
        checkin = validate_checkin(
            prior_mileage_km=vehicle.prior_mileage_km,
            **fields,
        )
    except InvalidCheckinError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    checkin_store.save(
        shop_id=claims.shop_id,
        demo_session_id=claims.demo_session_id,
        vehicle_id=vehicle_id,
        checkin=checkin,
    )
    return _checkin_response(checkin)


@app.get("/vehicles/{vehicle_id}/check-in", response_model=CheckinResponse)
def get_checkin(
    vehicle_id: str,
    claims: Annotated[SessionClaims, Depends(current_session)],
) -> CheckinResponse:
    checkin = checkin_store.get(
        shop_id=claims.shop_id,
        demo_session_id=claims.demo_session_id,
        vehicle_id=vehicle_id,
    )
    if checkin is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Check-in not found")
    return _checkin_response(checkin)


def _evaluate_for_vehicle(
    claims: SessionClaims,
    vehicle: CanonicalVehicle,
    current_mileage_km: int,
    checked_in_on: str,
    *,
    allow_fallback_market: bool = False,
) -> Recommendation:
    """Retrieve evidence for this exact configuration and market, never a neighbouring one."""
    return evaluate_maintenance(
        current_mileage_km,
        checked_in_on,
        make=vehicle.make,
        model=vehicle.model,
        engine=vehicle.engine,
        drivetrain=vehicle.drivetrain,
        market=vehicle.market,
        allow_fallback_market=allow_fallback_market,
        completed_services=service_history_store.completed(claims.shop_id, vehicle.id),
        declined_services=service_history_store.declined(claims.shop_id, vehicle.id),
    )


@app.get("/vehicles/{vehicle_id}/recommendation", response_model=RecommendationResponse)
def get_recommendation(
    vehicle_id: str,
    claims: Annotated[SessionClaims, Depends(current_session)],
    allow_fallback_market: bool = False,
) -> RecommendationResponse:
    vehicle = vehicle_store.get(shop_id=claims.shop_id, vehicle_id=vehicle_id)
    if vehicle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    checkin = checkin_store.get(shop_id=claims.shop_id, demo_session_id=claims.demo_session_id, vehicle_id=vehicle_id)
    if checkin is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Confirm a check-in before requesting recommendations")
    recommendation = _evaluate_for_vehicle(
        claims,
        vehicle,
        checkin.current_mileage_km,
        checkin.checked_in_on,
        allow_fallback_market=allow_fallback_market,
    )
    return RecommendationResponse(
        state=recommendation.state,
        actionable=recommendation.actionable,
        service_code=recommendation.service_code,
        rule_version=recommendation.rule_version,
        due_reason=recommendation.due_reason,
        citation_page=recommendation.citation_page,
        citation_section=recommendation.citation_section,
        confidence=recommendation.confidence,
        warnings=list(recommendation.warnings),
        declined_service_ids=list(recommendation.declined_service_ids),
    )


def _build_quote_draft(shop_id: str, engine: str, service_codes: list[str]) -> QuoteDraft:
    parts = {
        part_number: operations_store.part(shop_id, part_number)
        for part_number in required_part_numbers(service_codes)
    }
    return draft_quote(
        service_codes,
        engine=engine,
        parts=parts,
        slots=operations_store.slots(shop_id),
    )


@app.post(
    "/vehicles/{vehicle_id}/quote-drafts",
    response_model=QuoteDraftResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_quote_draft(
    vehicle_id: str,
    request: QuoteDraftRequest,
    claims: Annotated[SessionClaims, Depends(current_session)],
) -> QuoteDraftResponse:
    vehicle = vehicle_store.get(shop_id=claims.shop_id, vehicle_id=vehicle_id)
    if vehicle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    checkin = checkin_store.get(
        shop_id=claims.shop_id,
        demo_session_id=claims.demo_session_id,
        vehicle_id=vehicle_id,
    )
    if checkin is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Confirm a check-in before drafting a quote",
        )
    try:
        draft = _build_quote_draft(claims.shop_id, vehicle.engine, request.service_codes)
    except (UnknownServiceError, InformationalServiceError) as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error
    return QuoteDraftResponse(
        lines=[QuoteLineResponse(**line.__dict__) for line in draft.lines],
        subtotal_mxn=draft.subtotal_mxn,
        iva_mxn=draft.iva_mxn,
        total_mxn=draft.total_mxn,
        duration_minutes=draft.duration_minutes,
        bay_slot_id=draft.bay_slot_id,
        warnings=list(draft.warnings),
    )


class QuoteContext(NamedTuple):
    facts: QuoteFacts
    citations: QuoteCitations
    fingerprint: str
    unavailable_service_codes: tuple[str, ...]
    declines_per_service: tuple[int, ...]


def _quote_context(
    claims: SessionClaims, vehicle_id: str, service_codes: list[str]
) -> QuoteContext:
    """Recompute the volatile quote inputs an approval command depends on."""
    vehicle = vehicle_store.get(shop_id=claims.shop_id, vehicle_id=vehicle_id)
    if vehicle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    checkin = checkin_store.get(
        shop_id=claims.shop_id,
        demo_session_id=claims.demo_session_id,
        vehicle_id=vehicle_id,
    )
    if checkin is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Confirm a check-in before reviewing a quote",
        )
    try:
        draft = _build_quote_draft(claims.shop_id, vehicle.engine, service_codes)
    except (UnknownServiceError, InformationalServiceError) as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error
    recommendation = _evaluate_for_vehicle(
        claims, vehicle, checkin.current_mileage_km, checkin.checked_in_on
    )
    facts = QuoteFacts(
        service_codes=tuple(service_codes),
        subtotal_mxn=draft.subtotal_mxn,
        iva_mxn=draft.iva_mxn,
        total_mxn=draft.total_mxn,
        duration_minutes=draft.duration_minutes,
        bay_slot_id=draft.bay_slot_id,
    )
    citations = QuoteCitations(
        rule_version=recommendation.rule_version,
        citation_page=recommendation.citation_page,
        citation_section=recommendation.citation_section,
    )
    declined = service_history_store.declined(claims.shop_id, vehicle_id)
    return QuoteContext(
        facts=facts,
        citations=citations,
        fingerprint=fingerprint(draft),
        unavailable_service_codes=tuple(
            line.service_code for line in draft.lines if not line.available
        ),
        declines_per_service=tuple(
            sum(1 for record in declined if record.service_code == service_code)
            for service_code in service_codes
        ),
    )


def _assess(context: QuoteContext, invalidation_reason: str | None) -> EscalationAssessment:
    return assess_escalation(
        total_mxn=context.facts.total_mxn,
        rule_version=context.citations.rule_version,
        citation_page=context.citations.citation_page,
        declines_per_service=context.declines_per_service,
        invalidation_reason=invalidation_reason,
        unavailable_service_codes=context.unavailable_service_codes,
    )


def _facts_response(facts: QuoteFacts) -> QuoteFactsResponse:
    return QuoteFactsResponse(
        service_codes=list(facts.service_codes),
        subtotal_mxn=facts.subtotal_mxn,
        iva_mxn=facts.iva_mxn,
        total_mxn=facts.total_mxn,
        duration_minutes=facts.duration_minutes,
        bay_slot_id=facts.bay_slot_id,
    )


def _review_response(
    review: QuoteReview, claims: SessionClaims, escalation: EscalationAssessment
) -> QuoteReviewResponse:
    return QuoteReviewResponse(
        id=review.id,
        vehicle_id=review.vehicle_id,
        approver_role=claims.role,
        approver_session_id=claims.demo_session_id,
        facts=_facts_response(review.facts),
        citations=QuoteCitationsResponse(**review.citations.__dict__),
        status=review.status,
        invalidation_reason=review.invalidation_reason,
        escalation_required=escalation.required,
        escalation_reasons=list(escalation.reasons),
        evidence_blocked=escalation.evidence_blocked,
        blocking_reason=escalation.blocking_reason,
    )


def _decision_response(decision: QuoteDecision) -> QuoteDecisionResponse:
    return QuoteDecisionResponse(
        id=decision.id,
        review_id=decision.review_id,
        quote_id=decision.quote_id,
        decision=decision.decision,
        approver_role=decision.approver_role,
        approver_session_id=decision.approver_session_id,
        reason=decision.reason,
        facts=_facts_response(decision.facts),
        citations=QuoteCitationsResponse(**decision.citations.__dict__),
        escalation_reasons=list(decision.escalation_reasons),
    )


def _load_review(review_id: str, claims: SessionClaims) -> QuoteReview:
    try:
        return quote_command_store.get(review_id, claims.shop_id, claims.demo_session_id)
    except (KeyError, PermissionError) as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Quote review not found"
        ) from error


@app.post(
    "/vehicles/{vehicle_id}/quote-reviews",
    response_model=QuoteReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
def open_quote_review(
    vehicle_id: str,
    request: QuoteDraftRequest,
    claims: Annotated[SessionClaims, Depends(current_session)],
) -> QuoteReviewResponse:
    context = _quote_context(claims, vehicle_id, request.service_codes)
    review = quote_command_store.open_review(
        shop_id=claims.shop_id,
        demo_session_id=claims.demo_session_id,
        vehicle_id=vehicle_id,
        facts=context.facts,
        citations=context.citations,
        fingerprint=context.fingerprint,
    )
    return _review_response(review, claims, _assess(context, review.invalidation_reason))


@app.get("/quote-reviews/{review_id}", response_model=QuoteReviewResponse)
def get_quote_review(
    review_id: str,
    claims: Annotated[SessionClaims, Depends(current_session)],
) -> QuoteReviewResponse:
    review = _load_review(review_id, claims)
    context = _quote_context(claims, review.vehicle_id, list(review.facts.service_codes))
    revalidated = quote_command_store.revalidate(review.id, context.facts, context.fingerprint)
    return _review_response(
        revalidated, claims, _assess(context, revalidated.invalidation_reason)
    )


@app.get("/quote-audit", response_model=list[QuoteDecisionResponse])
def list_quote_audit(
    claims: Annotated[SessionClaims, Depends(current_session)],
) -> list[QuoteDecisionResponse]:
    if claims.role not in ("manager", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Manager role is required"
        )
    return [_decision_response(decision) for decision in quote_command_store.audit_trail(claims.shop_id)]


@app.post("/quote-reviews/{review_id}/decision", response_model=QuoteDecisionResponse)
def decide_quote_review(
    review_id: str,
    request: QuoteDecisionRequest,
    claims: Annotated[SessionClaims, Depends(current_session)],
) -> QuoteDecisionResponse:
    review = _load_review(review_id, claims)
    context = _quote_context(claims, review.vehicle_id, list(review.facts.service_codes))
    escalation = _assess(context, review.invalidation_reason)
    if request.decision == "reject":
        if not (request.reason or "").strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="A rejection reason is required",
            )
        return _decision_response(
            quote_command_store.reject(
                review.id,
                shop_id=claims.shop_id,
                demo_session_id=claims.demo_session_id,
                approver_role=claims.role,
                approver_session_id=claims.demo_session_id,
                reason=request.reason or "",
                escalation_reasons=escalation.reasons,
            )
        )

    try:
        decision = quote_command_store.approve(
            review.id,
            shop_id=claims.shop_id,
            demo_session_id=claims.demo_session_id,
            approver_role=claims.role,
            approver_session_id=claims.demo_session_id,
            idempotency_key=request.idempotency_key,
            current_facts=context.facts,
            current_fingerprint=context.fingerprint,
            escalation=escalation,
            reason=request.reason,
        )
    except EvidenceInsufficientError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error
    except EscalationRequiredError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    except EscalationReasonRequiredError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error
    except StaleQuoteError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    return _decision_response(decision)


class ApprovedQuoteContext(NamedTuple):
    decision: QuoteDecision
    review: QuoteReview
    customer_label: str
    slot_label: str


def _approved_quote(quote_id: str, claims: SessionClaims) -> ApprovedQuoteContext:
    """Load an approved quote and its slot; every message step depends on this gate."""
    try:
        decision, review = quote_command_store.approved_quote(
            quote_id, claims.shop_id, claims.demo_session_id
        )
    except KeyError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A human approval is required before reserving or messaging",
        ) from error
    except PermissionError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Approved quote not found"
        ) from error
    if decision.facts.bay_slot_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="The approved quote has no bay slot"
        )
    slot = next(
        (
            slot
            for slot in operations_store.slots(claims.shop_id)
            if slot.id == decision.facts.bay_slot_id
        ),
        None,
    )
    if slot is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="The approved bay slot is no longer offered"
        )
    vehicle = vehicle_store.get(shop_id=claims.shop_id, vehicle_id=review.vehicle_id)
    if vehicle is None:  # pragma: no cover - protected by the review boundary
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    return ApprovedQuoteContext(decision, review, vehicle.customer_label, slot.starts_at)


def _appointment_response(appointment: Appointment) -> AppointmentResponse:
    return AppointmentResponse(
        id=appointment.id,
        quote_id=appointment.quote_id,
        bay_slot_id=appointment.bay_slot_id,
        starts_at=appointment.starts_at,
        approver_role=appointment.approver_role,
        simulated=appointment.simulated,
    )


def _delivery_response(delivery: SmsDelivery) -> SmsDeliveryResponse:
    return SmsDeliveryResponse(
        id=delivery.id,
        quote_id=delivery.quote_id,
        text=delivery.text,
        segments=delivery.segments,
        state=delivery.state,
        simulated=delivery.simulated,
        approver_role=delivery.approver_role,
        rule_version=delivery.rule_version,
        citation_page=delivery.citation_page,
        citation_section=delivery.citation_section,
    )


@app.post(
    "/quotes/{quote_id}/appointment",
    response_model=AppointmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def reserve_appointment(
    quote_id: str,
    claims: Annotated[SessionClaims, Depends(current_session)],
) -> AppointmentResponse:
    context = _approved_quote(quote_id, claims)
    appointment = appointment_store.reserve(
        quote_id=quote_id,
        shop_id=claims.shop_id,
        demo_session_id=claims.demo_session_id,
        bay_slot_id=context.decision.facts.bay_slot_id or "",
        starts_at=context.slot_label,
        approver_role=context.decision.approver_role,
    )
    return _appointment_response(appointment)


@app.post("/quotes/{quote_id}/sms-preview", response_model=SmsPreviewResponse)
def preview_sms(
    quote_id: str,
    claims: Annotated[SessionClaims, Depends(current_session)],
) -> SmsPreviewResponse:
    context = _approved_quote(quote_id, claims)
    preview = compose_sms(
        customer_label=context.customer_label,
        service_codes=context.decision.facts.service_codes,
        total_mxn=context.decision.facts.total_mxn,
        slot_label=context.slot_label,
    )
    return SmsPreviewResponse(
        text=preview.text, segments=preview.segments, priorities=list(preview.priorities)
    )


@app.post(
    "/quotes/{quote_id}/messages",
    response_model=SmsDeliveryResponse,
    status_code=status.HTTP_201_CREATED,
)
def enqueue_sms(
    quote_id: str,
    request: SmsRequest,
    claims: Annotated[SessionClaims, Depends(current_session)],
) -> SmsDeliveryResponse:
    context = _approved_quote(quote_id, claims)
    if appointment_store.for_quote(quote_id, claims.shop_id, claims.demo_session_id) is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Reserve the appointment before enqueueing a message",
        )
    try:
        segments = validate_sms(
            request.text,
            customer_label=context.customer_label,
            service_codes=context.decision.facts.service_codes,
            total_mxn=context.decision.facts.total_mxn,
            slot_label=context.slot_label,
        )
    except (InventedContentError, MessageTooLongError) as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error
    delivery = messaging_store.enqueue(
        quote_id=quote_id,
        shop_id=claims.shop_id,
        demo_session_id=claims.demo_session_id,
        text=request.text,
        segments=segments,
        approver_role=context.decision.approver_role,
        rule_version=context.decision.citations.rule_version,
        citation_page=context.decision.citations.citation_page,
        citation_section=context.decision.citations.citation_section,
    )
    return _delivery_response(delivery)


@app.get("/messages/{delivery_id}", response_model=SmsDeliveryResponse)
def get_message(
    delivery_id: str,
    claims: Annotated[SessionClaims, Depends(current_session)],
) -> SmsDeliveryResponse:
    try:
        delivery = messaging_store.get(delivery_id, claims.shop_id, claims.demo_session_id)
    except (KeyError, PermissionError) as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Message not found"
        ) from error
    return _delivery_response(delivery)


@app.post("/messages/{delivery_id}/advance", response_model=SmsDeliveryResponse)
def advance_message(
    delivery_id: str,
    claims: Annotated[SessionClaims, Depends(current_session)],
) -> SmsDeliveryResponse:
    try:
        delivery = messaging_store.advance(delivery_id, claims.shop_id, claims.demo_session_id)
    except (KeyError, PermissionError) as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Message not found"
        ) from error
    return _delivery_response(delivery)


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


def _load_voice_note(note_id: str, claims: SessionClaims) -> VoiceNote:
    try:
        return voice_note_store.get(note_id, claims.shop_id, claims.demo_session_id)
    except (KeyError, PermissionError) as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Voice note not found"
        ) from error


@app.post(
    "/voice-notes", response_model=VoiceNoteResponse, status_code=status.HTTP_201_CREATED
)
def create_voice_note(
    request: VoiceNoteRequest,
    claims: Annotated[SessionClaims, Depends(current_session)],
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
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error
    return _voice_response(voice_note_store.save(note))


@app.post("/voice-notes/{note_id}/confirmation", response_model=VoiceNoteResponse)
def confirm_voice_note(
    note_id: str,
    request: ConfirmTranscriptRequest,
    claims: Annotated[SessionClaims, Depends(current_session)],
) -> VoiceNoteResponse:
    note = _load_voice_note(note_id, claims)
    try:
        confirmed = confirm(note, request.transcript)
    except UnconfirmedTranscriptError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error
    return _voice_response(voice_note_store.save(confirmed))


@app.get("/voice-notes/{note_id}/trace")
def get_voice_trace(
    note_id: str,
    claims: Annotated[SessionClaims, Depends(current_session)],
) -> dict[str, object]:
    return trace_payload(_load_voice_note(note_id, claims))


@app.get("/admin/evaluation", response_model=EvaluationReportResponse)
def get_evaluation_report(
    claims: Annotated[SessionClaims, Depends(current_session)],
) -> EvaluationReportResponse:
    if claims.role not in ("manager", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Manager role is required"
        )
    report = run_suite()
    return EvaluationReportResponse(
        case_count=len(report.results),
        scores=report.scores,
        thresholds_met=report.thresholds_met,
        kinds=report.kinds,
        dataset_version=report.dataset_version,
        prompt_version=report.prompt_version,
        provider=report.provider,
        rule_versions=list(report.rule_versions),
        failing_case_ids=[result.case_id for result in report.results if not result.passed],
    )


@app.post("/service-questions", response_model=ServiceQuestionResponse)
def answer_service_question(
    request: ServiceQuestionRequest,
    claims: Annotated[SessionClaims, Depends(current_session)],
) -> ServiceQuestionResponse:
    try:
        result = semantic_gateway.run(request.question, claims.shop_id)
    except UnsupportedQuestionError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error
    except UnsafeSqlError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    except QueryTimeoutError as error:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=str(error)
        ) from error
    return ServiceQuestionResponse(
        answer=result.answer,
        sql=result.query.sql,
        rows=[[str(value) for value in row] for row in result.rows],
        retrieval=RetrievalMetadataResponse(
            views=list(result.query.views),
            columns=list(result.query.columns),
            row_limit=result.query.row_limit,
            timeout_seconds=result.query.timeout_seconds,
            principal=result.query.principal,
        ),
    )


def _run_response(run: AdvisorRun) -> AdvisorRunResponse:
    return AdvisorRunResponse(id=run.id, events=list(run.events), decision=run.decision, command_executed=run.command_executed)


@app.post("/advisor-runs", response_model=AdvisorRunResponse, status_code=status.HTTP_201_CREATED)
def start_advisor_run(claims: Annotated[SessionClaims, Depends(current_session)]) -> AdvisorRunResponse:
    return _run_response(workflow_store.start(claims.shop_id, claims.demo_session_id))


@app.get("/advisor-runs/{run_id}", response_model=AdvisorRunResponse)
def resume_advisor_run(run_id: str, claims: Annotated[SessionClaims, Depends(current_session)]) -> AdvisorRunResponse:
    try:
        return _run_response(workflow_store.reconnect(run_id, claims.shop_id, claims.demo_session_id))
    except (KeyError, PermissionError) as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Advisor run not found") from error


@app.get("/advisor-runs/{run_id}/events")
def stream_advisor_run_events(run_id: str, claims: Annotated[SessionClaims, Depends(current_session)]) -> StreamingResponse:
    try:
        run = workflow_store.reconnect(run_id, claims.shop_id, claims.demo_session_id)
    except (KeyError, PermissionError) as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Advisor run not found") from error
    return StreamingResponse((f"data: {event}\n\n" for event in run.events), media_type="text/event-stream")


@app.post("/advisor-runs/{run_id}/decision", response_model=AdvisorRunResponse)
def decide_advisor_run(run_id: str, request: AdvisorDecisionRequest, claims: Annotated[SessionClaims, Depends(current_session)]) -> AdvisorRunResponse:
    workflow_store.reconnect(run_id, claims.shop_id, claims.demo_session_id)
    return _run_response(workflow_store.decide(run_id, request.decision))


@app.post("/explanations", response_model=ExplanationResponse)
def create_explanation(request: ExplanationRequest, claims: Annotated[SessionClaims, Depends(current_session)]) -> ExplanationResponse:
    del claims
    explanation = explain_recommendation(evaluate_civic_maintenance(request.current_mileage_km, "2026-07-27", evidence_available=request.evidence_available))
    return ExplanationResponse(**explanation.__dict__)


@app.post("/contextual-chat", response_model=ExplanationResponse)
def contextual_chat(request: ChatRequest, claims: Annotated[SessionClaims, Depends(current_session)]) -> ExplanationResponse:
    del claims
    reply = answer_contextual_question(request.question, evaluate_civic_maintenance(request.current_mileage_km, "2026-07-27"), request.provider_available)
    return ExplanationResponse(**reply.__dict__)
