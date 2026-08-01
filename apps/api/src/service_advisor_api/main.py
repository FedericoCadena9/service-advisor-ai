"""FastAPI application composition."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from service_advisor_api.routers import (
    admin,
    appointments,
    health,
    insights,
    quotes,
    runs,
    sessions,
    vehicles,
    voice,
)
from service_advisor_api.state import (  # noqa: F401
    operations_store,
    semantic_gateway,
    service_history_store,
)

app = FastAPI(title="Service Advisor API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:4173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(health.router)
app.include_router(sessions.router)
app.include_router(vehicles.router)
app.include_router(quotes.router)
app.include_router(appointments.router)
app.include_router(voice.router)
app.include_router(runs.router)
app.include_router(insights.router)
app.include_router(admin.router)
