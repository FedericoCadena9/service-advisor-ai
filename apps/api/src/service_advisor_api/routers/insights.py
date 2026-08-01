"""Grounded explanations, contextual chat, and read-only service questions."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status

from service_advisor_api import state
from service_advisor_api.auth import SessionClaims
from service_advisor_api.chat import answer_contextual_question
from service_advisor_api.explanations import explain_recommendation
from service_advisor_api.recommendations import Recommendation, evaluate_maintenance
from service_advisor_api.routers.dependencies import current_session
from service_advisor_api.routers.schemas import (
    ChatRequest,
    ExplanationRequest,
    ExplanationResponse,
    RetrievalMetadataResponse,
    ServiceQuestionRequest,
    ServiceQuestionResponse,
)
from service_advisor_api.text_to_sql import (
    QueryFailedError,
    QueryTimeoutError,
    UnsafeSqlError,
    UnsupportedQuestionError,
)

router = APIRouter()
DEMO_MODEL = "deterministic-demo"


def _recommendation_for_request(
    claims: SessionClaims,
    vehicle_id: str,
    current_mileage_km: int,
    *,
    evidence_available: bool = True,
) -> Recommendation:
    vehicle = state.vehicle_store.get(shop_id=claims.shop_id, vehicle_id=vehicle_id)
    if vehicle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    return evaluate_maintenance(
        current_mileage_km,
        datetime.now(UTC).date().isoformat(),
        make=vehicle.make,
        model=vehicle.model,
        engine=vehicle.engine,
        drivetrain=vehicle.drivetrain,
        market=vehicle.market,
        evidence_available=evidence_available,
        completed_services=state.service_history_store.completed(claims.shop_id, vehicle_id),
        declined_services=state.service_history_store.declined(claims.shop_id, vehicle_id),
    )


@router.post("/explanations", response_model=ExplanationResponse)
def create_explanation(
    request: ExplanationRequest,
    claims: Annotated[SessionClaims, Depends(current_session)],
    x_trace_id: Annotated[str | None, Header()] = None,
) -> ExplanationResponse:
    recommendation = _recommendation_for_request(
        claims,
        request.vehicle_id,
        request.current_mileage_km,
        evidence_available=request.evidence_available,
    )
    explanation = explain_recommendation(recommendation)
    state.record_span(
        x_trace_id,
        name="explanation",
        kind="provider",
        cost_mxn=state.PROVIDER_CALL_COST_MXN,
        attributes={
            "model": DEMO_MODEL,
            "degraded": explanation.degraded,
            "citation_page": explanation.citation_page,
        },
    )
    return ExplanationResponse(**explanation.__dict__)


@router.post("/contextual-chat", response_model=ExplanationResponse)
def contextual_chat(
    request: ChatRequest,
    claims: Annotated[SessionClaims, Depends(current_session)],
    x_trace_id: Annotated[str | None, Header()] = None,
) -> ExplanationResponse:
    reply = answer_contextual_question(
        request.question,
        _recommendation_for_request(claims, request.vehicle_id, request.current_mileage_km),
        state.language_provider,
    )
    state.record_span(
        x_trace_id,
        name="contextual_chat",
        kind="provider",
        cost_mxn=state.PROVIDER_CALL_COST_MXN,
        attributes={
            "model": state.language_provider.name,
            "degraded": reply.degraded,
            "citation_page": reply.citation_page,
        },
    )
    return ExplanationResponse(**reply.__dict__)


@router.post("/service-questions", response_model=ServiceQuestionResponse)
def answer_service_question(
    request: ServiceQuestionRequest,
    claims: Annotated[SessionClaims, Depends(current_session)],
) -> ServiceQuestionResponse:
    try:
        result = state.semantic_gateway.run(request.question, claims.shop_id)
    except UnsupportedQuestionError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    except UnsafeSqlError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    except QueryFailedError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    except QueryTimeoutError as error:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=str(error)) from error
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
