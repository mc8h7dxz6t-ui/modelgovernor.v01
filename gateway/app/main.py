"""Governance gateway — OIDC-terminated reserve-before-dispatch proxy."""
from __future__ import annotations

import logging
import os
import uuid
from decimal import Decimal
from typing import Any

import httpx
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from .auth_oidc import GatewayAuthContext, require_dispatch_auth
from .config import Settings, get_settings
from .providers.router import get_provider_router

logger = logging.getLogger(__name__)


class GovernedDispatchRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=255)
    trace_id: str = Field(..., min_length=1, max_length=255)
    model: str = Field(..., min_length=1, max_length=255)
    estimated_cost: Decimal = Field(..., ge=0)
    idempotency_key: str | None = None
    prompt: str | None = Field(default=None, min_length=1)
    messages: list[dict[str, Any]] | None = None


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


app = FastAPI(title="modelgovernor gateway", version="0.3.0")


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
    return {"status": "ready", "provider_mode": settings.provider_mode}


@app.post("/governed/dispatch", response_model=GovernedDispatchResponse)
def governed_dispatch(
    request: GovernedDispatchRequest,
    auth: GatewayAuthContext = Depends(require_dispatch_auth),
) -> GovernedDispatchResponse:
    settings = _settings()
    idempotency_key = request.idempotency_key or f"gw-{uuid.uuid4().hex[:16]}"
    headers = {
        "x-internal-token": settings.sidecar_internal_token,
        "content-type": "application/json",
    }

    reserve_payload = {
        "user_id": request.user_id,
        "trace_id": request.trace_id,
        "idempotency_key": idempotency_key,
        "model": request.model,
        "estimated_cost": str(request.estimated_cost),
    }
    with httpx.Client(timeout=settings.provider_timeout_seconds + 5.0) as client:
        reserve = client.post(
            f"{settings.sidecar_url.rstrip('/')}/reserve",
            headers=headers,
            json=reserve_payload,
        )
        if reserve.status_code >= 400:
            raise HTTPException(status_code=reserve.status_code, detail=reserve.text)
        reserve_body = reserve.json()

        provider_result = get_provider_router().dispatch(
            settings=settings,
            model=request.model,
            prompt=request.prompt,
            messages=request.messages,
        )
        actual_cost = min(provider_result.actual_cost, request.estimated_cost)

        settle_payload = {
            "idempotency_key": idempotency_key,
            "outcome": "SETTLED",
            "actual_cost": str(actual_cost),
            "provider_request_id": provider_result.provider_request_id,
            "provider_name": provider_result.provider_name,
            "model": provider_result.model,
            "input_tokens": provider_result.input_tokens,
            "output_tokens": provider_result.output_tokens,
            "cached_input_tokens": provider_result.cached_input_tokens,
            "cached_output_tokens": provider_result.cached_output_tokens,
            "latency_ms": provider_result.latency_ms,
        }
        settle = client.post(
            f"{settings.sidecar_url.rstrip('/')}/settle",
            headers=headers,
            json=settle_payload,
        )
        if settle.status_code >= 400:
            raise HTTPException(status_code=settle.status_code, detail=settle.text)
        settle_body = settle.json()

    logger.info(
        "governed dispatch subject=%s provider=%s model=%s idempotency_key=%s cost=%s",
        auth.subject,
        provider_result.provider_name,
        provider_result.model,
        idempotency_key,
        actual_cost,
    )
    return GovernedDispatchResponse(
        idempotency_key=idempotency_key,
        reserve_status=reserve_body["status"],
        settle_status=settle_body["status"],
        actual_cost=actual_cost,
        provider_request_id=provider_result.provider_request_id,
        provider_name=provider_result.provider_name,
        model=provider_result.model,
        response_text=provider_result.response_text,
        input_tokens=provider_result.input_tokens,
        output_tokens=provider_result.output_tokens,
        latency_ms=provider_result.latency_ms,
        authenticated_subject=auth.subject,
    )


if __name__ == "__main__":
    import uvicorn

    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("GATEWAY_PORT", "8080")))
