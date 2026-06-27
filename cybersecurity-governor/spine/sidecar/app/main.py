from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Response
from sqlalchemy import text

from .config import get_settings
from .db import get_db_session
from .diagnostic_mode import diagnostic_snapshot
from .http_metrics import PrometheusMiddleware, prometheus_metrics_body
from .metrics import get_counters
from .routes_admin import router as admin_router
from .routes_commit import router as commit_router
from .routes_crystallize import router as crystallize_router
from .routes_regulatory import router as regulatory_router
from .schemas import HealthResponse


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    yield


app = FastAPI(title="cybersecuritygovernor-sidecar", version="0.2.0", lifespan=_lifespan)
app.add_middleware(PrometheusMiddleware)


@app.get("/healthz", response_model=HealthResponse)
def healthz() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/readyz", response_model=HealthResponse)
def readyz() -> HealthResponse:
    try:
        with get_db_session() as session:
            session.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="database unavailable") from exc
    return HealthResponse(status="ready", details=diagnostic_snapshot())


@app.get("/metrics.json")
def metrics_json() -> dict:
    return get_counters().snapshot()


@app.get("/metrics/prometheus")
def metrics_prometheus() -> Response:
    body = prometheus_metrics_body()
    if not body:
        raise HTTPException(status_code=503, detail="prometheus_client not installed")
    return Response(content=body, media_type="text/plain; version=0.0.4; charset=utf-8")


app.include_router(crystallize_router)
app.include_router(commit_router)
app.include_router(admin_router)
app.include_router(regulatory_router)
