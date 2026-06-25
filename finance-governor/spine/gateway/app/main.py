from decimal import Decimal
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .config import get_settings
from .governance import execute_governed_commit

app = FastAPI(title="financegovernor-gateway", version="0.2.0")


class GovernedCommitRequest(BaseModel):
    platform: str
    operation_id: str | None = None
    account_id: str = "desk-default"
    risk_tier: str = "high"
    facets: dict[str, Any] = Field(default_factory=dict)
    policy_id: str | None = None
    reserved_exposure: Decimal = Decimal("0")
    committed_exposure: Decimal = Decimal("0")
    outcome: str = "committed"


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


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
            reserved_exposure=request.reserved_exposure,
            committed_exposure=request.committed_exposure,
            outcome=request.outcome,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
