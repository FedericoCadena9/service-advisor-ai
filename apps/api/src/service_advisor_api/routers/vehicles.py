"""Vehicle search, check-in, history, and maintenance recommendation endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from service_advisor_api import state
from service_advisor_api.auth import SessionClaims
from service_advisor_api.checkins import Checkin, InvalidCheckinError, validate_checkin
from service_advisor_api.recommendations import Recommendation, evaluate_maintenance
from service_advisor_api.routers.dependencies import _load_voice_note, current_session
from service_advisor_api.routers.schemas import (
    CheckinRequest,
    CheckinResponse,
    RecommendationResponse,
    ServiceHistoryResponse,
    ServiceRecordResponse,
    VehicleSearchResponse,
    VehicleSummaryResponse,
)
from service_advisor_api.service_history import ServiceRecord
from service_advisor_api.vehicles import CanonicalVehicle, VehicleSearchResult
from service_advisor_api.voice import UnconfirmedTranscriptError, workflow_transcript

router = APIRouter()


@router.get("/vehicles/search", response_model=list[VehicleSearchResponse])
def search_vehicles(
    query: Annotated[str, Query(min_length=1)],
    claims: Annotated[SessionClaims, Depends(current_session)],
) -> list[VehicleSearchResult]:
    return state.vehicle_store.search(shop_id=claims.shop_id, query=query)


@router.get("/vehicles/{vehicle_id}", response_model=VehicleSummaryResponse)
def get_vehicle(
    vehicle_id: str, claims: Annotated[SessionClaims, Depends(current_session)]
) -> VehicleSummaryResponse:
    vehicle = state.vehicle_store.get(shop_id=claims.shop_id, vehicle_id=vehicle_id)
    if vehicle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    return VehicleSummaryResponse.model_validate(vehicle, from_attributes=True)


def _service_record_response(record: ServiceRecord) -> ServiceRecordResponse:
    return ServiceRecordResponse(id=record.id, service_code=record.service_code, status=record.status)


@router.get("/vehicles/{vehicle_id}/history", response_model=ServiceHistoryResponse)
def get_service_history(
    vehicle_id: str, claims: Annotated[SessionClaims, Depends(current_session)]
) -> ServiceHistoryResponse:
    return ServiceHistoryResponse(
        completed=[
            _service_record_response(record)
            for record in state.service_history_store.completed(claims.shop_id, vehicle_id)
        ],
        declined=[
            _service_record_response(record)
            for record in state.service_history_store.declined(claims.shop_id, vehicle_id)
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


@router.post(
    "/vehicles/{vehicle_id}/check-ins",
    response_model=CheckinResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_checkin(
    vehicle_id: str,
    request: CheckinRequest,
    claims: Annotated[SessionClaims, Depends(current_session)],
) -> CheckinResponse:
    vehicle = state.vehicle_store.get(shop_id=claims.shop_id, vehicle_id=vehicle_id)
    if vehicle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    fields = request.model_dump(exclude={"voice_note_id"})
    if request.voice_note_id is not None:
        try:
            fields["concern"] = workflow_transcript(_load_voice_note(request.voice_note_id, claims))
        except UnconfirmedTranscriptError as error:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    try:
        checkin = validate_checkin(prior_mileage_km=vehicle.prior_mileage_km, **fields)
    except InvalidCheckinError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    state.checkin_store.save(
        shop_id=claims.shop_id,
        demo_session_id=claims.demo_session_id,
        vehicle_id=vehicle_id,
        checkin=checkin,
    )
    return _checkin_response(checkin)


@router.get("/vehicles/{vehicle_id}/check-in", response_model=CheckinResponse)
def get_checkin(
    vehicle_id: str, claims: Annotated[SessionClaims, Depends(current_session)]
) -> CheckinResponse:
    checkin = state.checkin_store.get(
        shop_id=claims.shop_id, demo_session_id=claims.demo_session_id, vehicle_id=vehicle_id
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
    # A labeled foreign document is answered with its label; a caller that will only accept
    # a domestic one passes false and gets a refusal instead.
    allow_fallback_market: bool = True,
) -> Recommendation:
    return evaluate_maintenance(
        current_mileage_km,
        checked_in_on,
        make=vehicle.make,
        model=vehicle.model,
        engine=vehicle.engine,
        drivetrain=vehicle.drivetrain,
        market=vehicle.market,
        allow_fallback_market=allow_fallback_market,
        completed_services=state.service_history_store.completed(claims.shop_id, vehicle.id),
        declined_services=state.service_history_store.declined(claims.shop_id, vehicle.id),
    )


@router.get("/vehicles/{vehicle_id}/recommendation", response_model=RecommendationResponse)
def get_recommendation(
    vehicle_id: str,
    claims: Annotated[SessionClaims, Depends(current_session)],
    # A labeled foreign document is answered with its label; a caller that will only accept
    # a domestic one passes false and gets a refusal instead.
    allow_fallback_market: bool = True,
    x_trace_id: Annotated[str | None, Header()] = None,
) -> RecommendationResponse:
    vehicle = state.vehicle_store.get(shop_id=claims.shop_id, vehicle_id=vehicle_id)
    if vehicle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    checkin = state.checkin_store.get(
        shop_id=claims.shop_id, demo_session_id=claims.demo_session_id, vehicle_id=vehicle_id
    )
    if checkin is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Confirm a check-in before requesting recommendations",
        )
    recommendation = _evaluate_for_vehicle(
        claims,
        vehicle,
        checkin.current_mileage_km,
        checkin.checked_in_on,
        allow_fallback_market=allow_fallback_market,
    )
    state.record_span(
        x_trace_id,
        name="knowledge.retrieval",
        kind="retrieval",
        attributes={
            "vehicle_id": vehicle_id,
            "rule_version": recommendation.rule_version,
            "citation_page": recommendation.citation_page,
            "state": recommendation.state,
            "confidence": recommendation.confidence,
        },
    )
    state.record_span(
        x_trace_id,
        name="read_recommendation",
        kind="tool",
        attributes={"tool": "read_recommendation", "actionable": recommendation.actionable},
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
