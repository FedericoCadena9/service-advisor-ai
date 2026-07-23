from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["healthy"]


app = FastAPI(title="Service Advisor API", version="0.1.0")


@app.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    return HealthResponse(status="healthy")
