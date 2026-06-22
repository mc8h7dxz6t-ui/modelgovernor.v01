from fastapi import FastAPI

from .routes_reserve import router as reserve_router
from .routes_settle import router as settle_router
from .schemas import HealthResponse

app = FastAPI(title="modelgovernor sidecar", version="0.1.0")


@app.get("/healthz", response_model=HealthResponse)
def healthz() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/readyz", response_model=HealthResponse)
def readyz() -> HealthResponse:
    return HealthResponse(status="ready")


app.include_router(reserve_router)
app.include_router(settle_router)
