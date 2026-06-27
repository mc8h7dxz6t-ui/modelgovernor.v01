"""Envoy external authorization (HTTP) adapter for EgressGovern allowlist."""
from __future__ import annotations

from typing import Any

from .egress_policy import EgressRequest, evaluate_egress


def _header_map(payload: dict[str, Any]) -> dict[str, str]:
    headers = (
        payload.get("attributes", {})
        .get("request", {})
        .get("http", {})
        .get("headers", {})
    )
    if isinstance(headers, dict):
        normalized: dict[str, str] = {}
        for key, value in headers.items():
            if isinstance(value, str):
                normalized[key.lower()] = value
            elif isinstance(value, list) and value:
                normalized[key.lower()] = str(value[0])
        return normalized
    return {}


def extract_destination_host(payload: dict[str, Any]) -> str:
    http = payload.get("attributes", {}).get("request", {}).get("http", {})
    host = http.get("host") or _header_map(payload).get(":authority") or _header_map(payload).get("host")
    if host:
        return str(host)
    path = str(http.get("path") or "")
    if path.startswith("http://") or path.startswith("https://"):
        from urllib.parse import urlparse

        parsed = urlparse(path)
        if parsed.hostname:
            return parsed.hostname
    raise ValueError("destination host not present in ext_authz request")


def evaluate_ext_authz(payload: dict[str, Any]) -> tuple[bool, str, str]:
    """Return (allowed, decision, reference)."""
    host = extract_destination_host(payload)
    http = payload.get("attributes", {}).get("request", {}).get("http", {})
    flow_id = str(http.get("id") or http.get("path") or host)[:128]
    decision, reference = evaluate_egress(
        EgressRequest(flow_id=flow_id, destination_host=host),
    )
    return decision == "ALLOWED", decision, reference
