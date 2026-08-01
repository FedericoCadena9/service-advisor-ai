"""Demo-session and visitor-workspace endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from service_advisor_api import state
from service_advisor_api.auth import SessionClaims, create_demo_session, verify_demo_session
from service_advisor_api.overlays import DemoOverlay
from service_advisor_api.routers.dependencies import current_session
from service_advisor_api.routers.schemas import (
    CreateDemoSessionRequest,
    DemoSessionResponse,
    WorkspaceResponse,
)

router = APIRouter()


@router.post("/demo-sessions", response_model=DemoSessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(request: CreateDemoSessionRequest) -> DemoSessionResponse:
    token = create_demo_session(request.role)
    claims = verify_demo_session(token)
    return DemoSessionResponse(token=token, role=claims.role, expires_at=claims.expires_at.isoformat())


def _workspace_response(claims: SessionClaims, overlay: DemoOverlay) -> WorkspaceResponse:
    return WorkspaceResponse(
        shop_id=claims.shop_id,
        demo_session_id=claims.demo_session_id,
        role=claims.role,
        generation=overlay.generation,
    )


@router.get("/workspace", response_model=WorkspaceResponse)
def get_workspace(claims: Annotated[SessionClaims, Depends(current_session)]) -> WorkspaceResponse:
    overlay = state.overlay_store.get_or_create(
        shop_id=claims.shop_id, demo_session_id=claims.demo_session_id, role=claims.role
    )
    return _workspace_response(claims, overlay)


@router.post("/workspace/reset", response_model=WorkspaceResponse)
def reset_workspace(claims: Annotated[SessionClaims, Depends(current_session)]) -> WorkspaceResponse:
    overlay = state.overlay_store.reset(
        shop_id=claims.shop_id, demo_session_id=claims.demo_session_id, role=claims.role
    )
    return _workspace_response(claims, overlay)


@router.get("/admin/demo-sessions", response_model=list[WorkspaceResponse])
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
        for overlay in state.overlay_store.list_for_shop(claims.shop_id)
    ]
