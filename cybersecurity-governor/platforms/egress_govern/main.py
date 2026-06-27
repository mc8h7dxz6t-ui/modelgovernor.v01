"""EgressGovern — runtime egress allowlist commit gate (not just Istio config)."""
from __future__ import annotations

import hashlib

from fastapi import FastAPI, HTTPException
from typing import Any

from platforms.common.platform_sdk import GovernedPlatform, spine_health_payload

from .egress_policy import EgressRequest, allowlist, evaluate_egress, normalize_host
from .ext_authz import evaluate_ext_authz

app = FastAPI(title="egressgovern", version="0.1.0")
_GOVERNED = GovernedPlatform("egress_govern")


@app.get("/healthz")
def healthz() -> dict:
    return spine_health_payload("egress_govern")


@app.get("/readyz")
def readyz() -> dict:
    return healthz()


@app.post("/egress/evaluate")
def evaluate(request: EgressRequest) -> dict:
    decision, reference = evaluate_egress(request)
    facets = {
        "flow_id": request.flow_id,
        "destination_host": normalize_host(request.destination_host),
        "destination_port": request.destination_port,
        "protocol": request.protocol,
        "egress_decision": decision,
        "reference": reference,
    }
    crystal_id = _GOVERNED.govern_operation(
        request.flow_id,
        facets,
        decision=decision,
        reserve_amount="0",
        account_id=request.account_id,
        outcome=decision.lower(),
    )
    if decision != "ALLOWED":
        raise HTTPException(status_code=403, detail={"decision": decision, "reference": reference})
    return {"decision": decision, "crystal_id": crystal_id, "reference": reference}


@app.get("/egress/allowlist")
def list_allowlist() -> dict:
    hosts = sorted(allowlist())
    digest = hashlib.sha256(",".join(hosts).encode()).hexdigest()
    return {"hosts": hosts, "digest_sha256": digest}


@app.post("/envoy/authz/check")
def envoy_ext_authz(payload: dict[str, Any]) -> dict:
    """Envoy HTTP external authorization adapter — real dataplane integration point."""
    try:
        allowed, decision, reference = evaluate_ext_authz(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not allowed:
        raise HTTPException(
            status_code=403,
            detail={"decision": decision, "reference": reference, "source": "egress_govern"},
        )
    return {"status": "ok", "decision": decision, "reference": reference}
