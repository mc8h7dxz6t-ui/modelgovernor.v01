#!/usr/bin/env python3
"""Embedded attestation rehearsal — real probes via in-process FastAPI (no Docker).

Use when Docker is unavailable. For investor-grade artifacts prefer:
  make cg-full-rehearsal
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
IG = ROOT / "cybersecurity-governor"
ARTIFACTS = ROOT / "artifacts" / "reliability" / "cybersecurity-governor"
SIDECAR = IG / "spine" / "sidecar"
PLATFORMS = IG / "platforms"

sys.path.insert(0, str(SIDECAR))
sys.path.insert(0, str(PLATFORMS))


@contextmanager
def _spine_client():
    from sqlalchemy import create_engine, text
    from sqlalchemy.pool import StaticPool
    from fastapi.testclient import TestClient

    schema = (IG / "tests" / "schema_sqlite.sql").read_text()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    with engine.begin() as conn:
        for stmt in schema.split(";"):
            s = stmt.strip()
            if s:
                conn.execute(text(s))

    from app.config import Settings, override_settings
    from app.db import override_engine
    from app.guardrails import reset_guardrails

    settings = Settings(
        database_url="sqlite+pysqlite:///:memory:",
        redis_url="redis://localhost:6381/0",
        cg_internal_tokens="dev-cg-spine-token-change-me",
    )
    override_settings(settings)
    override_engine(engine)
    reset_guardrails()

    from app.main import app

    headers = {"x-internal-token": "dev-cg-spine-token-change-me"}
    with TestClient(app) as client:
        yield client, headers

    reset_guardrails()


@contextmanager
def _claim_gate_client():
    from fastapi.testclient import TestClient

    os.environ["CG_SPINE_ENABLED"] = "false"
    from platforms.claim_gate.main import app

    with TestClient(app) as client:
        yield client


def _probe(name: str, fn: Callable[[], None]) -> dict[str, Any]:
    try:
        fn()
        return {"name": name, "status": "pass"}
    except Exception as exc:  # noqa: BLE001
        return {"name": name, "status": "fail", "error": str(exc)}


def run_embedded_attestation() -> dict[str, Any]:
    probes: list[dict[str, Any]] = []

    with _spine_client() as (sidecar, headers):
        probes.append(_probe("spine_ready", lambda: sidecar.get("/readyz").raise_for_status()))

        def governed_commit() -> None:
            r = sidecar.post(
                "/crystallize",
                headers=headers,
                json={
                    "platform": "claim_gate",
                    "operation_id": f"embedded-{int(datetime.now(timezone.utc).timestamp())}",
                    "account_id": "tenant-default",
                    "risk_tier": "high",
                    "facets": {"claim_id": "embedded-attest", "payout_amount": "100.00"},
                    "policy_id": "claim-high-us",
                    "reserved_budget": "100",
                },
            )
            r.raise_for_status()
            crystal_id = r.json()["crystal_id"]
            c = sidecar.post(
                "/commit",
                headers=headers,
                json={
                    "crystal_id": crystal_id,
                    "facets": {"claim_id": "embedded-attest", "payout_amount": "100.00"},
                    "committed_budget": "100",
                    "outcome": "paid",
                },
            )
            c.raise_for_status()

        probes.append(_probe("governed_commit", governed_commit))

        def verify_chain() -> None:
            r = sidecar.get("/internal/security/verify-chain", headers=headers)
            r.raise_for_status()
            if not r.json().get("valid"):
                raise RuntimeError(r.json())

        probes.append(_probe("verify_chain", verify_chain))
        probes.append(
            _probe(
                "anchor_head",
                lambda: sidecar.post("/internal/security/anchor-head", headers=headers).raise_for_status(),
            )
        )

    with _claim_gate_client() as claim_gate:
        probes.append(
            _probe(
                "claim_gate_evaluate",
                lambda: claim_gate.post(
                    "/claim/evaluate",
                    json={
                        "claim_id": "embedded-gate-depth",
                        "payout_amount": "5000.00",
                        "policy_number": "POL-AUTO-001",
                        "idempotency_key": "embedded-pay-depth",
                    },
                ).raise_for_status(),
            )
        )
        probes.append(
            _probe(
                "claim_gate_fnol_guidewire",
                lambda: claim_gate.post(
                    "/claim/fnol/webhook",
                    json={
                        "vendor": "guidewire",
                        "payload": {
                            "claim": {
                                "claimNumber": "embedded-fnol-gw",
                                "reportedAmount": "8000.00",
                                "policyNumber": "POL-AUTO-001",
                                "lossDate": "2025-06-01",
                                "id": "gw-evt-embedded",
                            }
                        },
                    },
                ).raise_for_status(),
            )
        )
        probes.append(
            _probe(
                "claim_gate_fnol_acturis_uk",
                lambda: claim_gate.post(
                    "/claim/fnol/webhook",
                    json={
                        "vendor": "acturis",
                        "payload": {
                            "notification": {
                                "claimReference": "ACT-UK-EMBED",
                                "policyReference": "POL-MOTOR-UK-001",
                                "dateOfLoss": "2025-05-20",
                                "estimatedAmount": "4500.00",
                                "currencyCode": "GBP",
                                "notificationId": "act-evt-embedded",
                            }
                        },
                    },
                ).raise_for_status(),
            )
        )

    passed = sum(1 for p in probes if p["status"] == "pass")
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "attestation_type": "cluster",
        "environment": os.environ.get("CG_ATTESTATION_ENV", "local-embedded-rehearsal"),
        "design_partner": os.environ.get("CG_DESIGN_PARTNER_NAME", "[REDACTED_CARRIER]"),
        "cluster_id": os.environ.get("CG_CLUSTER_ID", "cg-embedded-rehearsal-001"),
        "endpoints": {"mode": "embedded_testclient", "note": "Prefer make cg-full-rehearsal on Docker for HTTP stack"},
        "probes_total": len(probes),
        "probes_passed": passed,
        "probes_failed": len(probes) - passed,
        "certification": passed == len(probes),
        "probes": probes,
    }


def write_artifacts(report: dict[str, Any]) -> Path:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, indent=2, sort_keys=True)
    report["artifact_sha256"] = hashlib.sha256(payload.encode()).hexdigest()
    payload = json.dumps(report, indent=2, sort_keys=True)
    out = ARTIFACTS / "cluster_attestation.json"
    out.write_text(payload)
    return out


def main() -> int:
    report = run_embedded_attestation()
    path = write_artifacts(report)
    print(json.dumps(report, indent=2))
    print(f"\nWrote {path}", file=sys.stderr)
    if report["probes_failed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
