"""Advisor workflow lifecycle and server-sent event endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from service_advisor_api import state
from service_advisor_api.auth import SessionClaims
from service_advisor_api.evaluation import DATASET_VERSION, PROMPT_VERSION
from service_advisor_api.observability import TraceVersions
from service_advisor_api.routers.dependencies import current_session
from service_advisor_api.routers.schemas import AdvisorDecisionRequest, AdvisorRunResponse
from service_advisor_api.workflows import AdvisorRun

router = APIRouter()
DEMO_MODEL = "deterministic-demo"


def _run_response(run: AdvisorRun) -> AdvisorRunResponse:
    return AdvisorRunResponse(
        id=run.id,
        events=list(run.events),
        decision=run.decision,
        command_executed=run.command_executed,
        trace_id=run.trace_id,
    )


@router.post("/advisor-runs", response_model=AdvisorRunResponse, status_code=status.HTTP_201_CREATED)
def start_advisor_run(
    claims: Annotated[SessionClaims, Depends(current_session)],
) -> AdvisorRunResponse:
    trace_id = state.trace_recorder.start_trace(
        claims.shop_id,
        TraceVersions(
            rule_version=None,
            prompt_version=PROMPT_VERSION,
            dataset_version=DATASET_VERSION,
            model=DEMO_MODEL,
        ),
    )
    run = state.workflow_store.start(claims.shop_id, claims.demo_session_id, trace_id)
    state.record_span(
        trace_id,
        name="advisor_run.start",
        kind="workflow",
        attributes={"run_id": run.id, "events": len(run.events), "role": claims.role},
    )
    state.record_span(
        trace_id,
        name="POST /advisor-runs",
        kind="http",
        attributes={"status_code": 201, "shop_id": claims.shop_id},
    )
    return _run_response(run)


@router.get("/advisor-runs/{run_id}", response_model=AdvisorRunResponse)
def resume_advisor_run(
    run_id: str, claims: Annotated[SessionClaims, Depends(current_session)]
) -> AdvisorRunResponse:
    try:
        run = state.workflow_store.reconnect(run_id, claims.shop_id, claims.demo_session_id)
    except (KeyError, PermissionError) as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Advisor run not found") from error
    state.record_span(
        run.trace_id,
        name="advisor_run.resume",
        kind="workflow",
        attributes={"run_id": run.id, "events": len(run.events)},
    )
    return _run_response(run)


@router.get("/advisor-runs/{run_id}/events")
def stream_advisor_run_events(
    run_id: str, claims: Annotated[SessionClaims, Depends(current_session)]
) -> StreamingResponse:
    try:
        run = state.workflow_store.reconnect(run_id, claims.shop_id, claims.demo_session_id)
    except (KeyError, PermissionError) as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Advisor run not found") from error
    state.record_span(
        run.trace_id,
        name="GET /advisor-runs/{run_id}/events",
        kind="http",
        attributes={"status_code": 200, "events": len(run.events)},
    )
    return StreamingResponse(
        (f"data: {event}\n\n" for event in run.events), media_type="text/event-stream"
    )


@router.post("/advisor-runs/{run_id}/decision", response_model=AdvisorRunResponse)
def decide_advisor_run(
    run_id: str,
    request: AdvisorDecisionRequest,
    claims: Annotated[SessionClaims, Depends(current_session)],
) -> AdvisorRunResponse:
    state.workflow_store.reconnect(run_id, claims.shop_id, claims.demo_session_id)
    run = state.workflow_store.decide(run_id, request.decision)
    state.record_span(
        run.trace_id,
        name="advisor_run.decision",
        kind="command",
        attributes={
            "run_id": run.id,
            "decision": run.decision,
            "command_executed": run.command_executed,
            "role": claims.role,
        },
    )
    return _run_response(run)
