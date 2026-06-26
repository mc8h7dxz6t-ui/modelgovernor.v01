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
LEVEL = os.environ.get("FG_CERTIFICATION_LEVEL", "L2_INSTITUTIONAL")


def _run(cmd: list[str], env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=ROOT.parent, capture_output=True, text=True, env=env)


def main() -> int:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    base_env = {
        **os.environ,
        "PYTHONPATH": f"{ROOT}/spine/sidecar:{ROOT}",
        "FG_SPINE_ENABLED": "false",
    }
    tier1 = _run(
        [sys.executable, "-m", "pytest", "finance-governor/tests/", "-q", "--ignore=finance-governor/tests/chaos"],
        base_env,
    )
    tier2 = None
    if os.environ.get("FG_POSTGRES_TEST_URL") or os.environ.get("POSTGRES_TEST_URL"):
        tier2_env = {**base_env, "FG_POSTGRES_TEST_URL": os.environ.get("FG_POSTGRES_TEST_URL") or os.environ.get("POSTGRES_TEST_URL", "")}
        tier2 = _run(
            [sys.executable, "-m", "pytest", "finance-governor/tests/integration/", "-q"],
            tier2_env,
        )
    tier4 = None
    if os.environ.get("FG_POSTGRES_TEST_URL") and os.environ.get("FG_TOXIPROXY_API", os.environ.get("TOXIPROXY_API")):
        tier4 = _run(
            [sys.executable, "-m", "pytest", "finance-governor/tests/chaos/", "-q"],
            base_env,
        )
    mg_crosswire = _run(
        [sys.executable, "-m", "pytest", "tests/integration/test_mg_fg_crosswire.py", "-q"],
        {**os.environ, "PYTHONPATH": str(ROOT.parent)},
    )

    cert_level = LEVEL
    if tier2 and tier2.returncode == 0 and tier4 and tier4.returncode == 0:
        cert_level = "L4_GOLD"
    elif tier2 and tier2.returncode == 0:
        cert_level = "L3_INSTITUTIONAL_PLUS"

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "certification_level": cert_level,
        "platforms": [
            "algofreeze",
            "wire_match",
            "subledger_sync",
            "asset_ledger",
            "credit_govern",
        ],
        "tier1_exit_code": tier1.returncode,
        "tier1_summary": tier1.stdout.strip().splitlines()[-1] if tier1.stdout else "",
        "tier2_exit_code": tier2.returncode if tier2 else None,
        "tier2_summary": tier2.stdout.strip().splitlines()[-1] if tier2 and tier2.stdout else None,
        "tier4_exit_code": tier4.returncode if tier4 else None,
        "tier4_summary": tier4.stdout.strip().splitlines()[-1] if tier4 and tier4.stdout else None,
        "mg_fg_crosswire_exit_code": mg_crosswire.returncode,
        "l4_capabilities": {
            "postgres_integration": tier2.returncode == 0 if tier2 else False,
            "toxiproxy_chaos": tier4.returncode == 0 if tier4 else False,
            "mg_fg_crosswire": mg_crosswire.returncode == 0,
            "s3_chain_anchor_api": True,
            "k8s_ha_helm": "deploy/helm/financegovernor",
            "s3_infra_template": "deploy/infra/aws/fg-ledger-anchor-bucket.yaml",
        },
        "competitive_gaps_bridged": {
            "algofreeze": ["ci_cd_deploy_sha_registry", "mg_reserve_crosswire"],
            "wire_match": ["semantic_gate", "iso20022", "mesh_block"],
            "subledger_sync": ["fx_snapshot_hash_at_match"],
            "asset_ledger": ["reg_table_version_pinning"],
            "credit_govern": ["reserve_before_score"],
            "spine_mesh": ["no_wire_while_algo_frozen"],
        },
    }
    out = ARTIFACTS / "latest_certification.json"
    out.write_text(json.dumps(report, indent=2) + "\n")
    sha = hashlib.sha256(out.read_bytes()).hexdigest()
    (ARTIFACTS / "latest_certification.sha256").write_text(sha + "\n")
    print(json.dumps(report, indent=2))
    exit_codes = [tier1.returncode, mg_crosswire.returncode]
    if tier2:
        exit_codes.append(tier2.returncode)
    if tier4:
        exit_codes.append(tier4.returncode)
    return max(exit_codes)


if __name__ == "__main__":
    raise SystemExit(main())
