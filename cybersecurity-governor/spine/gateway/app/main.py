from decimal import Decimal
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .config import get_settings
from .governance import execute_governed_commit

app = FastAPI(title="cybersecuritygovernor-gateway", version="0.1.0")


class GovernedCommitRequest(BaseModel):
    platform: str
    operation_id: str | None = None
    account_id: str = "tenant-default"
    risk_tier: str = "high"
    facets: dict[str, Any] = Field(default_factory=dict)
    policy_id: str | None = None
    reserved_budget: Decimal = Decimal("0")
    committed_budget: Decimal = Decimal("0")
    outcome: str = "committed"


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.get("/readyz")
def readyz() -> dict:
    settings = get_settings()
    try:
        with httpx.Client(timeout=3.0) as client:
            response = client.get(f"{settings.cg_sidecar_url.rstrip('/')}/readyz")
            response.raise_for_status()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"sidecar unavailable: {exc}") from exc
    return {"status": "ready", "sidecar": "ok"}


@app.post("/governed/commit")
def governed_commit(request: GovernedCommitRequest) -> dict:
    try:
        return execute_governed_commit(
            get_settings(),
            platform=request.platform,
            operation_id=request.operation_id,
            account_id=request.account_id,
            risk_tier=request.risk_tier,
            facets=request.facets,
            policy_id=request.policy_id,
            reserved_budget=request.reserved_budget,
            committed_budget=request.committed_budget,
            outcome=request.outcome,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
