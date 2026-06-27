from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import text

from .config import get_settings
from .db import get_db_session
from .diagnostic_mode import diagnostic_snapshot
from .guardrails import get_guardrails
from .http_metrics import PrometheusMiddleware
from .metrics import get_counters
from .routes_admin import router as admin_router
from .routes_attribution import router as attribution_router
from .routes_metrics import router as metrics_router
from .routes_regulatory import router as regulatory_router
from .routes_reserve import router as reserve_router
from .routes_settle import router as settle_router
from .schemas import HealthResponse
from .tracing import setup_tracing


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    settings = get_settings()
    setup_tracing(service_name=settings.otel_service_name, otlp_endpoint=settings.otel_exporter_endpoint)
    yield


app = FastAPI(title="modelgovernor sidecar", version="0.1.0", lifespan=_lifespan)
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
    guardrail_status = get_guardrails().redis_status()
    guardrail_status.update(diagnostic_snapshot())
    return HealthResponse(status="ready", details=guardrail_status)


@app.get("/metrics.json", response_model=dict[str, int])
def metrics_json() -> JSONResponse:
    return JSONResponse(content=get_counters().snapshot())


app.include_router(reserve_router)
app.include_router(settle_router)
app.include_router(admin_router)
app.include_router(attribution_router)
app.include_router(regulatory_router)
app.include_router(metrics_router)
