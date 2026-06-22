from fastapi import FastAPI, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.config import get_settings
from app.metrics import registry as metrics_registry
from app.routes_reconcile import router as reconcile_router
from app.routes_reserve import router as reserve_router
from app.routes_settle import router as settle_router
from app.schemas import HealthResponse

app = FastAPI(title="modelgovernor sidecar", version="0.2.0")


@app.get("/healthz", response_model=HealthResponse)
def healthz() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/readyz", response_model=HealthResponse)
def readyz() -> HealthResponse:
    return HealthResponse(status="ready")


@app.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    settings = get_settings()
    if not settings.metrics_enabled:
        return Response(status_code=404)
    return Response(content=generate_latest(metrics_registry), media_type=CONTENT_TYPE_LATEST)


app.include_router(reserve_router)
app.include_router(settle_router)
app.include_router(reconcile_router)
