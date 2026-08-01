"""Manager and administrator observability, evaluation, and knowledge endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from service_advisor_api import state
from service_advisor_api.auth import SessionClaims
from service_advisor_api.evaluation import run_suite
from service_advisor_api.observability import quality_dashboard
from service_advisor_api.routers.dependencies import _require_manager, current_session
from service_advisor_api.routers.schemas import (
    DashboardResponse,
    EvaluationReportResponse,
    TraceResponse,
)

router = APIRouter()


@router.get("/admin/knowledge/civic-rule")
def inspect_civic_rule(
    claims: Annotated[SessionClaims, Depends(current_session)],
) -> dict[str, dict[str, object]]:
    if claims.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role is required")
    return state.knowledge_pack.inspection()


@router.get("/admin/traces/{trace_id}", response_model=TraceResponse)
def get_trace(
    trace_id: str, claims: Annotated[SessionClaims, Depends(current_session)]
) -> TraceResponse:
    _require_manager(claims)
    try:
        return TraceResponse.model_validate(state.trace_recorder.export(trace_id, claims.shop_id))
    except PermissionError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trace not found") from error


@router.get("/admin/dashboard", response_model=DashboardResponse)
def get_quality_dashboard(
    claims: Annotated[SessionClaims, Depends(current_session)],
) -> DashboardResponse:
    _require_manager(claims)
    audit = state.quote_command_store.audit_trail(claims.shop_id)
    report = run_suite()
    return DashboardResponse.model_validate(
        quality_dashboard(
            state.trace_recorder,
            claims.shop_id,
            escalation_outcomes={
                "approved": sum(1 for entry in audit if entry.decision == "approved"),
                "rejected": sum(1 for entry in audit if entry.decision == "rejected"),
                "escalated": sum(1 for entry in audit if entry.escalation_reasons),
            },
            evaluation_thresholds_met=report.thresholds_met,
            evaluation_score=report.scores["overall"],
        )
    )


@router.get("/admin/evaluation", response_model=EvaluationReportResponse)
def get_evaluation_report(
    claims: Annotated[SessionClaims, Depends(current_session)],
) -> EvaluationReportResponse:
    _require_manager(claims)
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
