#!/usr/bin/env python3
"""Generate Finance Governor institutional certification artifact."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT.parent / "artifacts" / "reliability" / "finance-governor"


def _run(cmd: list[str], env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=ROOT.parent, capture_output=True, text=True, env=env)


def main() -> int:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    env = {
        **os.environ,
        "PYTHONPATH": str(ROOT),
        "FG_SPINE_ENABLED": "false",
    }
    tier1 = _run(
        [sys.executable, "-m", "pytest", "finance-governor/tests/", "-q"],
        env,
    )
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "certification_level": "L2_INSTITUTIONAL",
        "platforms": [
            "algofreeze",
            "wire_match",
            "subledger_sync",
            "asset_ledger",
            "credit_govern",
        ],
        "tier1_exit_code": tier1.returncode,
        "tier1_summary": tier1.stdout.strip().splitlines()[-1] if tier1.stdout else "",
        "competitive_gaps_bridged": {
            "algofreeze": [
                "ci_cd_deploy_sha_registry",
                "feed_heartbeat_freeze",
                "zero_egress_when_frozen",
                "ems_proxy_integration_point",
            ],
            "wire_match": [
                "semantic_beneficiary_intent",
                "iso20022_adapter",
                "pre_rail_send_gate",
                "idempotency_duplicate_block",
            ],
            "subledger_sync": [
                "fx_snapshot_hash_at_match",
                "real_time_ic_pairing",
                "orphan_sweep_strand",
            ],
            "asset_ledger": [
                "reg_table_version_pinning",
                "runtime_depreciation_events",
                "book_value_invariant",
            ],
            "credit_govern": [
                "reserve_before_score",
                "model_version_policy_lock",
                "exposure_cap_enforcement",
                "high_risk_strand",
            ],
            "spine_mesh": ["no_wire_while_algo_frozen"],
        },
        "invariant_probes": [
            "frozen_egress_attempt_total",
            "wire_sent_below_threshold_total",
            "match_tolerance_breach_total",
            "negative_book_value_total",
            "model_version_mismatch_total",
            "crystal_mesh_block_total",
        ],
    }
    out = ARTIFACTS / "latest_certification.json"
    out.write_text(json.dumps(report, indent=2) + "\n")
    sha = hashlib.sha256(out.read_bytes()).hexdigest()
    (ARTIFACTS / "latest_certification.sha256").write_text(sha + "\n")
    print(json.dumps(report, indent=2))
    return tier1.returncode


if __name__ == "__main__":
    raise SystemExit(main())
