"""Governance gateway — reserve-before-dispatch proxy to the policy sidecar."""
from __future__ import annotations

import logging
import os
import uuid
from decimal import Decimal

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    sidecar_url: str = "http://sidecar:8081"
    sidecar_internal_token: str = "dev-token"
    mock_dispatch_cost: Decimal = Decimal("1.000000")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class GovernedDispatchRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=255)
    trace_id: str = Field(..., min_length=1, max_length=255)
    model: str = Field(..., min_length=1, max_length=255)
    estimated_cost: Decimal = Field(..., ge=0)
    idempotency_key: str | None = None


class GovernedDispatchResponse(BaseModel):
    idempotency_key: str
    reserve_status: str
    settle_status: str
    actual_cost: Decimal
    provider_request_id: str


settings = Settings()
app = FastAPI(title="modelgovernor gateway", version="0.1.0")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
def readyz() -> dict[str, str]:
    try:
        response = httpx.get(f"{settings.sidecar_url.rstrip('/')}/readyz", timeout=2.0)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="sidecar unavailable") from exc
    return {"status": "ready"}


@app.post("/governed/dispatch", response_model=GovernedDispatchResponse)
def governed_dispatch(request: GovernedDispatchRequest) -> GovernedDispatchResponse:
    idempotency_key = request.idempotency_key or f"gw-{uuid.uuid4().hex[:16]}"
    provider_request_id = f"provider-{idempotency_key}"
    headers = {"x-internal-token": settings.sidecar_internal_token, "content-type": "application/json"}

    reserve_payload = {
        "user_id": request.user_id,
        "trace_id": request.trace_id,
        "idempotency_key": idempotency_key,
        "model": request.model,
        "estimated_cost": str(request.estimated_cost),
    }
    with httpx.Client(timeout=10.0) as client:
        reserve = client.post(
            f"{settings.sidecar_url.rstrip('/')}/reserve",
            headers=headers,
            json=reserve_payload,
        )
        if reserve.status_code >= 400:
            raise HTTPException(status_code=reserve.status_code, detail=reserve.text)
        reserve_body = reserve.json()

        actual_cost = min(request.estimated_cost, settings.mock_dispatch_cost)
        settle_payload = {
            "idempotency_key": idempotency_key,
            "outcome": "SETTLED",
            "actual_cost": str(actual_cost),
            "provider_request_id": provider_request_id,
            "provider_name": request.model,
        }
        settle = client.post(
            f"{settings.sidecar_url.rstrip('/')}/settle",
            headers=headers,
            json=settle_payload,
        )
        if settle.status_code >= 400:
            raise HTTPException(status_code=settle.status_code, detail=settle.text)
        settle_body = settle.json()

    return GovernedDispatchResponse(
        idempotency_key=idempotency_key,
        reserve_status=reserve_body["status"],
        settle_status=settle_body["status"],
        actual_cost=actual_cost,
        provider_request_id=provider_request_id,
    )


if __name__ == "__main__":
    import uvicorn

    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("GATEWAY_PORT", "8080")))
