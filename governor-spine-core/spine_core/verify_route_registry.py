"""M1 verify-chain HTTP route registry."""

from __future__ import annotations

from dataclasses import dataclass

from pathlib import Path

from spine_core.config import DOMAIN_REGISTRY, GovernorDomain


@dataclass(frozen=True)
class VerifyRouteSpec:
    rel_path: str
    verify_fn: str


VERIFY_ROUTE_REGISTRY: dict[GovernorDomain, VerifyRouteSpec] = {
    GovernorDomain.MODEL: VerifyRouteSpec(
        rel_path="sidecar/app/routes_admin.py",
        verify_fn="verify_ledger_chain",
    ),
    GovernorDomain.FINANCE: VerifyRouteSpec(
        rel_path="finance-governor/spine/sidecar/app/routes_admin.py",
        verify_fn="verify_decision_chain",
    ),
    GovernorDomain.INSURANCE: VerifyRouteSpec(
        rel_path="insurance-governor/spine/sidecar/app/routes_admin.py",
        verify_fn="verify_claim_chain",
    ),
    GovernorDomain.CYBER: VerifyRouteSpec(
        rel_path="cybersecurity-governor/spine/sidecar/app/routes_admin.py",
        verify_fn="verify_security_chain",
    ),
}


def verify_route_path(domain: GovernorDomain) -> str:
    return DOMAIN_REGISTRY[domain].verify_path.lstrip("/internal/")
