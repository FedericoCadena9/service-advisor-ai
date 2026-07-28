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
from service_advisor_api.overlays import DemoOverlay, OverlayStore
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


app = FastAPI(title="Service Advisor API", version="0.1.0")
overlay_store = OverlayStore()
vehicle_store = CanonicalVehicleStore()
vehicle_store.seed()
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
