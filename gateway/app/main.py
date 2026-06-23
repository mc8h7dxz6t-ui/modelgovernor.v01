"""Governance gateway — OIDC-terminated reserve-before-dispatch proxy."""
from __future__ import annotations

import logging
import os
from decimal import Decimal

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

import httpx

from .auth_oidc import GatewayAuthContext, require_dispatch_auth
from .config import Settings, get_settings
from .governance import execute_governed_dispatch
from .openai_compat import router as openai_compat_router

logger = logging.getLogger(__name__)


class GovernedDispatchRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=255)
    trace_id: str = Field(..., min_length=1, max_length=255)
    model: str = Field(..., min_length=1, max_length=255)
    estimated_cost: Decimal = Field(..., ge=0)
    idempotency_key: str | None = None
    prompt: str | None = Field(default=None, min_length=1)
    messages: list[dict] | None = None


class GovernedDispatchResponse(BaseModel):
    idempotency_key: str
    reserve_status: str
    settle_status: str
    actual_cost: Decimal
    provider_request_id: str
    provider_name: str
    model: str
    response_text: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    authenticated_subject: str


def _settings() -> Settings:
    return get_settings()


app = FastAPI(title="modelgovernor gateway", version="0.4.0")
app.include_router(openai_compat_router)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
def readyz() -> dict[str, str]:
    settings = _settings()
    try:
        response = httpx.get(f"{settings.sidecar_url.rstrip('/')}/readyz", timeout=2.0)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="sidecar unavailable") from exc
    return {
        "status": "ready",
        "provider_mode": settings.provider_mode,
        "openai_compat_enabled": str(settings.openai_compat_enabled).lower(),
    }


@app.post("/governed/dispatch", response_model=GovernedDispatchResponse)
def governed_dispatch(
    request: GovernedDispatchRequest,
    auth: GatewayAuthContext = Depends(require_dispatch_auth),
) -> GovernedDispatchResponse:
    settings = _settings()
    outcome = execute_governed_dispatch(
        settings=settings,
        user_id=request.user_id,
        trace_id=request.trace_id,
        model=request.model,
        estimated_cost=request.estimated_cost,
        idempotency_key=request.idempotency_key,
        prompt=request.prompt,
        messages=request.messages,
        auth_subject=auth.subject,
    )
    return GovernedDispatchResponse(
        idempotency_key=outcome.idempotency_key,
        reserve_status=outcome.reserve_status,
        settle_status=outcome.settle_status,
        actual_cost=outcome.actual_cost,
        provider_request_id=outcome.provider_request_id,
        provider_name=outcome.provider_name,
        model=outcome.model,
        response_text=outcome.response_text,
        input_tokens=outcome.input_tokens,
        output_tokens=outcome.output_tokens,
        latency_ms=outcome.latency_ms,
        authenticated_subject=auth.subject,
    )


if __name__ == "__main__":
    import uvicorn

    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("GATEWAY_PORT", "8080")))
