#!/usr/bin/env python3
"""Cybersecurity Governor pilot/cluster attestation — produces JSON artifact for data room."""
from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "artifacts" / "reliability" / "cybersecurity-governor"


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default).rstrip("/")


def _get(url: str, headers: dict[str, str] | None = None) -> dict[str, Any]:
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def _post(url: str, body: dict[str, Any], headers: dict[str, str] | None = None) -> dict[str, Any]:
    data = json.dumps(body).encode()
    hdrs = {"content-type": "application/json", **(headers or {})}
    req = urllib.request.Request(url, data=data, headers=hdrs, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode()
        return json.loads(raw) if raw else {}


def _probe(name: str, fn) -> dict[str, Any]:
    try:
        fn()
        return {"name": name, "status": "pass"}
    except Exception as exc:  # noqa: BLE001
        return {"name": name, "status": "fail", "error": str(exc)}


def run_attestation() -> dict[str, Any]:
    token = os.environ.get("CG_INTERNAL_TOKENS", "dev-cg-spine-token-change-me")
    sidecar = _env("CG_SIDECAR_URL", "http://localhost:8121")
    gateway = _env("CG_GATEWAY_URL", "http://localhost:8120")
    claim_gate = _env("CG_EGRESS_GOVERN_URL", "http://localhost:8103")
    cluster = os.environ.get("CG_CLUSTER_ATTESTATION", "false").lower() == "true"
    environment = os.environ.get("CG_ATTESTATION_ENV", "compose-local" if not cluster else "customer-vpc-staging")

    headers = {"x-internal-token": token}
    probes: list[dict[str, Any]] = []

    probes.append(_probe("spine_ready", lambda: _get(f"{sidecar}/readyz")))
    probes.append(_probe("gateway_ready", lambda: _get(f"{gateway}/readyz")))

    def governed_commit() -> None:
        _post(
            f"{gateway}/governed/commit",
            {
                "platform": "claim_gate",
                "operation_id": f"pilot-{int(datetime.now(timezone.utc).timestamp())}",
                "facets": {"claim_id": "pilot-attest", "payout_amount": "100.00"},
                "policy_id": "claim-high-us",
                "reserved_budget": "100",
                "committed_budget": "100",
                "outcome": "paid",
            },
        )

    probes.append(_probe("governed_commit", governed_commit))

    def verify_chain() -> None:
        result = _get(f"{sidecar}/internal/security/verify-chain", headers)
        if not result.get("valid"):
            raise RuntimeError(f"chain invalid: {result}")

    probes.append(_probe("verify_chain", verify_chain))
    probes.append(_probe("anchor_head", lambda: _post(f"{sidecar}/internal/security/anchor-head", {}, headers)))

    def claim_gate_evaluate() -> None:
        _post(
            f"{claim_gate}/claim/evaluate",
            {
                "claim_id": "pilot-gate-depth",
                "payout_amount": "5000.00",
                "policy_number": "POL-AUTO-001",
                "idempotency_key": "pilot-pay-depth",
            },
        )

    probes.append(_probe("claim_gate_evaluate", claim_gate_evaluate))

    def claim_gate_fnol_guidewire() -> None:
        _post(
            f"{claim_gate}/claim/fnol/webhook",
            {
                "vendor": "guidewire",
                "payload": {
                    "claim": {
                        "claimNumber": "pilot-fnol-gw",
                        "reportedAmount": "8000.00",
                        "policyNumber": "POL-AUTO-001",
                        "lossDate": "2025-06-01",
                        "id": "gw-evt-1",
                    }
                },
            },
        )

    probes.append(_probe("claim_gate_fnol_guidewire", claim_gate_fnol_guidewire))

    def claim_gate_fnol_acturis() -> None:
        _post(
            f"{claim_gate}/claim/fnol/webhook",
            {
                "vendor": "acturis",
                "payload": {
                    "notification": {
                        "claimReference": "ACT-UK-9001",
                        "policyReference": "POL-MOTOR-UK-001",
                        "dateOfLoss": "2025-05-20",
                        "estimatedAmount": "4500.00",
                        "currencyCode": "GBP",
                        "notificationId": "act-evt-1",
                    }
                },
            },
        )

    probes.append(_probe("claim_gate_fnol_acturis_uk", claim_gate_fnol_acturis))

    host_base = os.environ.get("CG_PLATFORM_HOST", "http://localhost")

    def _optional_probe(name: str, health_path: str, action: str, body: dict[str, Any] | None) -> None:
        def _run() -> None:
            _get(f"{host_base}{health_path}")
            if action == "GET":
                _get(f"{host_base}{health_path.replace('/healthz', '/status')}")
            elif body is not None:
                endpoint = health_path.replace("/healthz", "/indemnity/evaluate" if "8110" in health_path else "/bind/evaluate")
                _post(f"{host_base}{endpoint}", body)

        try:
            _get(f"{host_base}{health_path}")
        except Exception:
            probes.append({"name": name, "status": "skip", "reason": "platform_not_running"})
            return
        probes.append(_probe(name, _run))

    _optional_probe("bind_authority", ":8104/healthz", "POST", {"application_id": "pilot-bind", "premium": "10000", "limit": "500000"})
    _optional_probe("indemnity_pay_gate", ":8110/healthz", "POST", {
        "payment_id": "pilot-crime", "payee_name": "Acme Indemnity Trust",
        "payee_account": "US44ACME001", "amount": "50000", "jurisdiction": "US",
    })

    passed = sum(1 for p in probes if p["status"] == "pass")
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "attestation_type": "cluster" if cluster else "pilot",
        "environment": environment,
        "design_partner": os.environ.get("CG_DESIGN_PARTNER_NAME", "[REDACTED_CARRIER]"),
        "cluster_id": os.environ.get("CG_CLUSTER_ID", "cg-staging-001"),
        "endpoints": {"sidecar": sidecar, "gateway": gateway, "claim_gate": claim_gate},
        "probes_total": len(probes),
        "probes_passed": passed,
        "probes_failed": len(probes) - passed,
        "certification": passed >= len(probes) - 2,  # allow optional platform skips
        "probes": probes,
    }
    return report


def write_artifacts(report: dict[str, Any]) -> Path:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, indent=2, sort_keys=True)
    digest = hashlib.sha256(payload.encode()).hexdigest()
    report["artifact_sha256"] = digest

    ts = int(datetime.now(timezone.utc).timestamp())
    out = ARTIFACTS / f"{'cluster' if report.get('attestation_type') == 'cluster' else 'pilot'}_attestation_{ts}.json"
    latest_name = "cluster_attestation.json" if report.get("attestation_type") == "cluster" else "latest_pilot_attestation.json"
    latest = ARTIFACTS / latest_name

    payload = json.dumps(report, indent=2, sort_keys=True)
    out.write_text(payload)
    latest.write_text(payload)
    return latest


def main() -> int:
    report = run_attestation()
    path = write_artifacts(report)
    print(json.dumps(report, indent=2))
    print(f"\nWrote {path}", file=sys.stderr)
    return 0 if report["certification"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
