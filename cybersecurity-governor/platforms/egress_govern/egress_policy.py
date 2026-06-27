"""EgressGovern allowlist policy — shared by HTTP API and Envoy ext_authz adapter."""
from __future__ import annotations

import os
from urllib.parse import urlparse

from pydantic import BaseModel

from platforms.common.platform_sdk import increment_invariant

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


def allowlist() -> frozenset[str]:
    raw = os.environ.get("EGRESS_ALLOWLIST", "")
    if not raw.strip():
        return DEFAULT_ALLOWLIST
    return frozenset(h.strip().lower() for h in raw.split(",") if h.strip())


def normalize_host(host: str) -> str:
    host = host.strip().lower()
    if "://" in host:
        parsed = urlparse(host)
        return (parsed.hostname or host).lower()
    return host.split(":")[0]


def evaluate_egress(req: EgressRequest) -> tuple[str, str]:
    host = normalize_host(req.destination_host)
    allowed = host in allowlist()
    if not allowed:
        increment_invariant("egress_govern", "egress_denied_total")
        if host.endswith(".onion") or host.startswith("169.254."):
            increment_invariant("egress_govern", "egress_shadow_it_blocked_total")
        return "DENIED", f"host not in allowlist: {host}"
    increment_invariant("egress_govern", "egress_allowlisted_total")
    return "ALLOWED", f"allowlisted:{host}"
