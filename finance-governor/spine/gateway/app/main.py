from decimal import Decimal
from typing import Any

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from .auth_oidc import GatewayAuthContext, require_governed_auth
from .config import get_settings
from .governance import execute_governed_commit
from .platform_proxy import list_platforms_from_sidecar, proxy_platform_request

app = FastAPI(title="financegovernor-gateway", version="0.3.0")


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


@app.get("/readyz")
def readyz() -> dict:
    settings = get_settings()
    try:
        response = httpx.get(f"{settings.fg_sidecar_url.rstrip('/')}/readyz", timeout=2.0)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="sidecar unavailable") from exc
    return {"status": "ready"}


@app.post("/governed/commit", dependencies=[Depends(require_governed_auth)])
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


@app.get("/platforms", dependencies=[Depends(require_governed_auth)])
def list_platforms() -> list[dict]:
    try:
        return list_platforms_from_sidecar(get_settings())
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="sidecar unavailable") from exc


@app.api_route(
    "/platforms/{platform_name}/proxy/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    dependencies=[Depends(require_governed_auth)],
)
async def platform_proxy(platform_name: str, path: str, request: Request) -> dict:
    settings = get_settings()
    json_body = None
    if request.method in {"POST", "PUT", "PATCH"}:
        try:
            json_body = await request.json()
        except Exception:
            json_body = None
    try:
        response = proxy_platform_request(
            settings,
            platform_name=platform_name,
            path=path,
            method=request.method,
            json_body=json_body,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if response.headers.get("content-type", "").startswith("application/json"):
        return response.json()
    return {"status_code": response.status_code, "body": response.text}
