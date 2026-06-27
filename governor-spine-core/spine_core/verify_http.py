"""HTTP chain verification — delegates to each governor's sidecar verify-chain API."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from spine_core.config import DOMAIN_PORTS, DOMAIN_REGISTRY, GovernorDomain


@dataclass
class VerifyResult:
    domain: GovernorDomain
    url: str
    valid: bool | None
    error: str | None = None
    raw: dict | None = None


def verify_domain_chain_http(
    domain: GovernorDomain,
    *,
    token: str = "dev-cg-spine-token-change-me",
    timeout_seconds: float = 5.0,
) -> VerifyResult:
    """Call sidecar verify-chain. Returns valid=None when sidecar is unreachable."""
    ports = DOMAIN_PORTS[domain]
    config = DOMAIN_REGISTRY[domain]
    url = f"http://127.0.0.1:{ports.sidecar}{config.verify_path}"
    req = urllib.request.Request(url, headers={"x-internal-token": token})
    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            payload = json.loads(resp.read().decode())
            return VerifyResult(
                domain=domain,
                url=url,
                valid=bool(payload.get("valid")),
                raw=payload,
            )
    except urllib.error.HTTPError as exc:
        return VerifyResult(domain=domain, url=url, valid=False, error=f"HTTP {exc.code}")
    except Exception as exc:  # noqa: BLE001
        return VerifyResult(domain=domain, url=url, valid=None, error=str(exc))


def verify_all_reachable(
    domains: tuple[GovernorDomain, ...] = (
        GovernorDomain.FINANCE,
        GovernorDomain.INSURANCE,
        GovernorDomain.CYBER,
    ),
    **kwargs,
) -> list[VerifyResult]:
    return [verify_domain_chain_http(domain, **kwargs) for domain in domains]
