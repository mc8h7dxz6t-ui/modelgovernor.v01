from fastapi import FastAPI
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from .metrics import get_counters
from .routes_audit import router as audit_router
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
    summary="Prometheus metrics",
    description=(
        "Returns Prometheus text exposition format for scraping by standard "
        "Prometheus-compatible collectors."
    ),
)
def metrics() -> Response:
    get_counters()
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get(
    "/metrics.json",
    summary="Invariant counter snapshot",
    description="Returns process-level invariant counters as JSON for test and load reports.",
)
def metrics_json() -> JSONResponse:
    return JSONResponse(content=get_counters().snapshot())


app.include_router(reserve_router)
app.include_router(settle_router)
app.include_router(reconcile_router)
app.include_router(audit_router)
