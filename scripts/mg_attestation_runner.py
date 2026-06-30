#!/usr/bin/env python3
"""ModelGovernor pilot attestation — produces JSON artifact for data room."""
from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SPINE_CORE = ROOT / "governor-spine-core"
if str(SPINE_CORE) not in sys.path:
    sys.path.insert(0, str(SPINE_CORE))

from spine_core.chain_verify_assert import assert_chain_verified  # noqa: E402

ARTIFACTS = ROOT / "artifacts" / "reliability" / "modelgovernor"


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default).rstrip("/")


def _token() -> str:
    raw = os.environ.get("SIDECAR_PRIMARY_TOKEN") or os.environ.get("SIDECAR_INTERNAL_TOKENS", "dev-sidecar-token")
    return raw.split(",")[0]


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
    token = _token()
    sidecar = _env("MG_SIDECAR_URL", "http://localhost:8081")
    gateway = _env("MG_GATEWAY_URL", "http://localhost:8080")
    environment = os.environ.get("MG_ATTESTATION_ENV", "compose-local")
    headers = {"x-internal-token": token}
    probes: list[dict[str, Any]] = []

    probes.append(_probe("spine_ready", lambda: _get(f"{sidecar}/readyz")))
    probes.append(_probe("gateway_ready", lambda: _get(f"{gateway}/readyz")))

    def governed_dispatch() -> None:
        _post(
            f"{gateway}/governed/dispatch",
            {
                "user_id": "smoke-user",
                "trace_id": f"trace-attest-{int(datetime.now(timezone.utc).timestamp())}",
                "model": "gpt-4o-mini",
                "estimated_cost": "1.000000",
                "idempotency_key": f"attest-{int(datetime.now(timezone.utc).timestamp())}",
                "prompt": "attestation probe",
            },
            headers,
        )

    probes.append(_probe("governed_dispatch", governed_dispatch))
    def verify_chain() -> None:
        result = _get(f"{sidecar}/internal/ledger/verify-chain", headers)
        assert_chain_verified(result, context="mg verify-chain")

    probes.append(_probe("verify_chain", verify_chain))
    probes.append(_probe("anchor_head", lambda: _post(f"{sidecar}/internal/ledger/anchor-head", {}, headers)))

    passed = sum(1 for p in probes if p["status"] == "pass")
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "attestation_type": "pilot",
        "environment": environment,
        "governor": "MODEL_GOVERNOR",
        "endpoints": {"sidecar": sidecar, "gateway": gateway},
        "probes_total": len(probes),
        "probes_passed": passed,
        "probes_failed": len(probes) - passed,
        "certification": passed == len(probes),
        "probes": probes,
    }
    return report


def write_artifacts(report: dict[str, Any]) -> Path:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    ts = int(datetime.now(timezone.utc).timestamp())
    out = ARTIFACTS / f"pilot_attestation_{ts}.json"
    latest = ARTIFACTS / "latest_pilot_attestation.json"
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
