"""Health and deployment-readiness endpoints."""

from typing import Literal

from fastapi import APIRouter, HTTPException, status

from service_advisor_api import state
from service_advisor_api.evaluation import run_suite
from service_advisor_api.release import (
    ReleaseGateError,
    qualify_release,
    release_gates,
    release_manifest,
    validate_migration,
)
from service_advisor_api.routers.schemas import (
    GateResultResponse,
    HealthResponse,
    ReadinessResponse,
    ReleaseManifestResponse,
)

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    return HealthResponse(status="healthy")


@router.get("/release", response_model=ReleaseManifestResponse)
def get_release_manifest() -> ReleaseManifestResponse:
    manifest = release_manifest()
    return ReleaseManifestResponse(
        release_version=manifest.release_version,
        model_version=manifest.model_version,
        prompt_version=manifest.prompt_version,
        dataset_version=manifest.dataset_version,
        rule_versions=list(manifest.rule_versions),
    )


@router.get("/readiness", response_model=ReadinessResponse)
def get_readiness() -> ReadinessResponse:
    """Cold-start aware readiness: the first request after scale-to-zero reports waking.

    Gate outcomes come from the deployment environment, never from the caller, so a public
    visitor cannot flip the smoke or live-model gates from a query string.
    """
    cold_start = not state.served_first_request
    state.served_first_request = True
    gates = release_gates(
        health_ok=True,
        smoke_ok=state.environment_flag("SMOKE_CHECK_PASSED", default=True),
        evaluation=run_suite(),
        live_model_promotion_approved=state.environment_flag(
            "LIVE_MODEL_PROMOTION_APPROVED", default=False
        ),
    )
    try:
        qualify_release(gates)
        status_value: Literal["ready", "waking"] = "waking" if cold_start else "ready"
    except ReleaseGateError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    return ReadinessResponse(
        status=status_value,
        cold_start=cold_start,
        manifest=get_release_manifest(),
        gates=[GateResultResponse(**gate.__dict__) for gate in gates],
        migration_steps=[step.name for step in validate_migration()],
    )
