#!/usr/bin/env python3
"""Cybersecurity Governor pilot/cluster attestation — produces JSON artifact for data room."""
from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SPINE_CORE = ROOT / "governor-spine-core"
if str(SPINE_CORE) not in sys.path:
    sys.path.insert(0, str(SPINE_CORE))

from spine_core.chain_verify_assert import assert_chain_verified  # noqa: E402

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


def _optional_url_probe(probes: list[dict[str, Any]], name: str, url: str, action) -> None:
    try:
        _get(url)
    except Exception:
        probes.append({"name": name, "status": "skip", "reason": "platform_not_running"})
        return
    probes.append(_probe(name, action))


def run_attestation() -> dict[str, Any]:
    token = os.environ.get("CG_INTERNAL_TOKENS", "dev-cg-spine-token-change-me")
    sidecar = _env("CG_SIDECAR_URL", "http://localhost:8121")
    gateway = _env("CG_GATEWAY_URL", "http://localhost:8120")
    egress = _env("CG_EGRESS_GOVERN_URL", "http://localhost:8123")
    identity = _env("CG_IDENTITY_GOVERN_URL", "http://localhost:8124")
    witness = _env("CG_WITNESS_BRIDGE_URL", "http://localhost:8129")
    lineage = _env("CG_LINEAGE_INGEST_URL", "http://localhost:8130")
    content = _env("CG_CONTENT_GUARD_URL", "http://localhost:8131")
    cluster = os.environ.get("CG_CLUSTER_ATTESTATION", "false").lower() == "true"
    environment = os.environ.get("CG_ATTESTATION_ENV", "compose-local" if not cluster else "customer-vpc-staging")

    headers = {"x-internal-token": token}
    probes = []

    probes.append(_probe("spine_ready", lambda: _get(f"{sidecar}/readyz")))
    probes.append(_probe("gateway_ready", lambda: _get(f"{gateway}/readyz")))

    def governed_commit() -> None:
        _post(
            f"{gateway}/governed/commit",
            {
                "platform": "egress_govern",
                "operation_id": f"pilot-{int(datetime.now(timezone.utc).timestamp())}",
                "facets": {
                    "flow_id": "pilot-attest",
                    "destination_host": "api.openai.com",
                    "egress_decision": "ALLOWED",
                },
                "policy_id": "egress-critical-us",
                "reserved_budget": "0",
                "committed_budget": "0",
                "outcome": "allowed",
            },
        )

    probes.append(_probe("governed_commit", governed_commit))

    def verify_chain() -> None:
        result = _get(f"{sidecar}/internal/security/verify-chain", headers)
        assert_chain_verified(result, context="cg verify-chain")

    probes.append(_probe("verify_chain", verify_chain))
    probes.append(_probe("anchor_head", lambda: _post(f"{sidecar}/internal/security/anchor-head", {}, headers)))

    probes.append(
        _probe(
            "egress_govern_evaluate",
            lambda: _post(f"{egress}/egress/evaluate", {"flow_id": "attest-1", "destination_host": "api.openai.com"}),
        )
    )
    probes.append(
        _probe(
            "identity_session_arm",
            lambda: _post(
                f"{identity}/session/arm",
                {
                    "session_id": "attest-session",
                    "user_id": "alice@corp.example",
                    "device_fingerprint": "dev_fp_trusted_workstation",
                    "client_ip": "10.0.1.42",
                },
            ),
        )
    )

    _optional_url_probe(
        probes,
        "witness_cloudtrail",
        f"{witness}/healthz",
        lambda: _post(
            f"{witness}/ingest/cloudtrail",
            {
                "detail": {
                    "eventName": "DeleteTrail",
                    "eventID": "attest-evt-1",
                    "userIdentity": {"arn": "arn:aws:iam::123:user/bob"},
                }
            },
        ),
    )
    _optional_url_probe(
        probes,
        "lineage_falco",
        f"{lineage}/healthz",
        lambda: _post(
            f"{lineage}/ingest/falco",
            {
                "rule": "Terminal shell in container",
                "priority": "Critical",
                "output_fields": {"proc.name": "bash", "user.name": "root"},
            },
        ),
    )
    _optional_url_probe(
        probes,
        "content_guard_evaluate",
        f"{content}/healthz",
        lambda: _post(
            f"{content}/content/evaluate",
            {
                "content_id": "attest-cg-1",
                "principal_id": "alice@corp.example",
                "text_body": "hello world",
            },
        ),
    )

    passed = sum(1 for p in probes if p["status"] == "pass")
    skipped = sum(1 for p in probes if p["status"] == "skip")
    required = [p for p in probes if p["status"] != "skip"]
    required_passed = sum(1 for p in required if p["status"] == "pass")
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "attestation_type": "cluster" if cluster else "pilot",
        "environment": environment,
        "design_partner": os.environ.get("CG_DESIGN_PARTNER_NAME", "[REDACTED_CARRIER]"),
        "cluster_id": os.environ.get("CG_CLUSTER_ID", "cg-staging-001"),
        "endpoints": {
            "sidecar": sidecar,
            "gateway": gateway,
            "egress_govern": egress,
            "identity_govern": identity,
            "witness_bridge": witness,
            "lineage_ingest": lineage,
            "content_guard": content,
        },
        "probes_total": len(probes),
        "probes_passed": passed,
        "probes_skipped": skipped,
        "probes_failed": len(required) - required_passed,
        "certification": required_passed == len(required),
        "probes": probes,
    }
    return report


def write_artifacts(report: dict[str, Any]) -> Path:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    ts = int(datetime.now(timezone.utc).timestamp())
    out = ARTIFACTS / f"{'cluster' if report.get('attestation_type') == 'cluster' else 'pilot'}_attestation_{ts}.json"
    latest_name = "cluster_attestation.json" if report.get("attestation_type") == "cluster" else "latest_pilot_attestation.json"
    latest = ARTIFACTS / latest_name
    payload = json.dumps(report, indent=2, sort_keys=True)
    digest = hashlib.sha256(payload.encode()).hexdigest()
    report["artifact_sha256"] = digest
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
