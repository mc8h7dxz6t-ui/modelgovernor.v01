from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .metrics import get_counters
from .routes_reconcile import router as reconcile_router
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


@app.get(
    "/metrics",
    summary="Invariant counter snapshot",
    description=(
        "Returns the current value of all process-level invariant counters as a "
        "JSON object.  Counters are cumulative since process start.  In a "
        "horizontally-scaled fleet each pod exposes its own counters; aggregate "
        "with your metrics scraper."
    ),
)
def metrics() -> JSONResponse:
    return JSONResponse(content=get_counters().snapshot())


app.include_router(reserve_router)
app.include_router(settle_router)
app.include_router(reconcile_router)
