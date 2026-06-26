"""EgressGovern — runtime egress allowlist commit gate (not just Istio config)."""
from __future__ import annotations

import hashlib
import os
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from platforms.common.platform_sdk import GovernedPlatform, increment_invariant, spine_health_payload

app = FastAPI(title="egressgovern", version="0.1.0")
_GOVERNED = GovernedPlatform("egress_govern")

DEFAULT_ALLOWLIST = frozenset(
    {
        "api.openai.com",
        "api.anthropic.com",
        "sidecar.cybersecuritygovernor.svc.cluster.local",
    }
)


class EgressRequest(BaseModel):
    flow_id: str
    destination_host: str
    destination_port: int = 443
    protocol: str = "https"
    account_id: str = "tenant-default"


def _allowlist() -> frozenset[str]:
    raw = os.environ.get("EGRESS_ALLOWLIST", "")
    if not raw.strip():
        return DEFAULT_ALLOWLIST
    return frozenset(h.strip().lower() for h in raw.split(",") if h.strip())


def _normalize_host(host: str) -> str:
    host = host.strip().lower()
    if "://" in host:
        parsed = urlparse(host)
        return (parsed.hostname or host).lower()
    return host.split(":")[0]


def evaluate_egress(req: EgressRequest) -> tuple[str, str]:
    host = _normalize_host(req.destination_host)
    allowed = host in _allowlist()
    if not allowed:
        increment_invariant("egress_govern", "egress_denied_total")
        if host.endswith(".onion") or host.startswith("169.254."):
            increment_invariant("egress_govern", "egress_shadow_it_blocked_total")
        return "DENIED", f"host not in allowlist: {host}"
    increment_invariant("egress_govern", "egress_allowlisted_total")
    return "ALLOWED", f"allowlisted:{host}"


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
        "destination_host": _normalize_host(request.destination_host),
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
    hosts = sorted(_allowlist())
    digest = hashlib.sha256(",".join(hosts).encode()).hexdigest()
    return {"hosts": hosts, "digest_sha256": digest}
