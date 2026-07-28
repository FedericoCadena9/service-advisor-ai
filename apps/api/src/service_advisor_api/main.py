from typing import Annotated, Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from service_advisor_api.auth import (
    ExpiredDemoSessionError,
    InvalidDemoSessionError,
    Role,
    SessionClaims,
    create_demo_session,
    verify_demo_session,
)
from service_advisor_api.checkins import (
    Checkin,
    CheckinStore,
    InvalidCheckinError,
    UseProfile,
    validate_checkin,
)
from service_advisor_api.knowledge import KnowledgePack
from service_advisor_api.overlays import DemoOverlay, OverlayStore
from service_advisor_api.recommendations import evaluate_civic_maintenance
from service_advisor_api.service_history import CivicServiceHistoryStore, ServiceRecord
from service_advisor_api.vehicles import CanonicalVehicleStore, VehicleSearchResult


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
    market: str
    prior_mileage_km: int
    prior_mileage_recorded_on: str
    is_demo_data: bool


class CheckinRequest(BaseModel):
    current_mileage_km: int
    checked_in_on: str
    use_profile: UseProfile
    severe_use_factors: list[str]
    concern: str
    appointment_window: str
    message_consent: bool


class CheckinResponse(CheckinRequest):
    prior_mileage_km: int


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


app = FastAPI(title="Service Advisor API", version="0.1.0")
overlay_store = OverlayStore()
vehicle_store = CanonicalVehicleStore()
vehicle_store.seed()
checkin_store = CheckinStore()
knowledge_pack = KnowledgePack()
service_history_store = CivicServiceHistoryStore()
service_history_store.seed()
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
    try:
        checkin = validate_checkin(
            prior_mileage_km=vehicle.prior_mileage_km,
            **request.model_dump(),
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


@app.get("/vehicles/{vehicle_id}/recommendation", response_model=RecommendationResponse)
def get_recommendation(
    vehicle_id: str,
    claims: Annotated[SessionClaims, Depends(current_session)],
) -> RecommendationResponse:
    checkin = checkin_store.get(shop_id=claims.shop_id, demo_session_id=claims.demo_session_id, vehicle_id=vehicle_id)
    if checkin is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Confirm a check-in before requesting recommendations")
    recommendation = evaluate_civic_maintenance(checkin.current_mileage_km, checkin.checked_in_on, completed_services=service_history_store.completed(claims.shop_id, vehicle_id), declined_services=service_history_store.declined(claims.shop_id, vehicle_id))
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
