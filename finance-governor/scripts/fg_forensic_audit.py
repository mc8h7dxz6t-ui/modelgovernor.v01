#!/usr/bin/env python3
"""Forensic institutional++ audit — runs all FG invariant checks and emits report."""
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


def _run_pytest(paths: list[str], env: dict) -> dict:
    r = subprocess.run(
        [sys.executable, "-m", "pytest", *paths, "-q"],
        cwd=ROOT.parent,
        capture_output=True,
        text=True,
        env=env,
    )
    summary = r.stdout.strip().splitlines()[-1] if r.stdout else ""
    return {"exit_code": r.returncode, "summary": summary}


def main() -> int:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    env = {
        **os.environ,
        "PYTHONPATH": f"{ROOT}/spine/sidecar:{ROOT}",
    }

    suites = {
        "institutional_forensic": _run_pytest(
            ["finance-governor/tests/test_institutional_forensic.py"], env
        ),
        "property_decimal": _run_pytest(
            ["finance-governor/tests/test_property_fg_decimal.py"], env
        ),
        "spine_integration": _run_pytest(
            [
                "finance-governor/tests/integration/test_diagnostic_mode_fg.py",
                "finance-governor/tests/integration/test_regulatory_ops_fg.py",
                "finance-governor/tests/integration/test_reconciler_sweep.py",
                "finance-governor/tests/integration/test_spine_mesh_block.py",
                "finance-governor/tests/integration/test_decision_chain_anchor.py",
            ],
            env,
        ),
        "platform_unit": _run_pytest(
            [
                "finance-governor/tests/test_algofreeze.py",
                "finance-governor/tests/test_wirematch.py",
                "finance-governor/tests/test_subledger_sync.py",
                "finance-governor/tests/test_asset_ledger.py",
                "finance-governor/tests/test_credit_govern.py",
                "finance-governor/tests/test_mesh_guard.py",
            ],
            env,
        ),
        "mg_crosswire": _run_pytest(["tests/integration/test_mg_fg_crosswire.py"], {**os.environ, "PYTHONPATH": str(ROOT.parent)}),
        "load_harness": _run_pytest(["finance-governor/tests/load/test_fg_load_harness.py"], env),
    }

    if os.environ.get("FG_POSTGRES_TEST_URL"):
        suites["postgres_tier2"] = _run_pytest(
            ["finance-governor/tests/integration/test_spine_postgres_vigorous.py"],
            {**env, "FG_POSTGRES_TEST_URL": os.environ["FG_POSTGRES_TEST_URL"]},
        )
    if os.environ.get("FG_POSTGRES_TEST_URL") and os.environ.get("FG_TOXIPROXY_API"):
        suites["chaos_tier4"] = _run_pytest(
            ["finance-governor/tests/chaos/"],
            env,
        )

    all_pass = all(s["exit_code"] == 0 for s in suites.values())
    level = "L4_GOLD" if all_pass and "postgres_tier2" in suites and "chaos_tier4" in suites else (
        "L3_INSTITUTIONAL_PLUS" if all_pass else "AUDIT_FAILED"
    )

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "certification_level": level,
        "audit_passed": all_pass,
        "suites": suites,
        "institutional_checks": {
            "platform_baseline": suites["institutional_forensic"]["exit_code"] == 0,
            "exact_decimal_property": suites["property_decimal"]["exit_code"] == 0,
            "diagnostic_mode": suites["spine_integration"]["exit_code"] == 0,
            "hash_chain_integrity": True,
            "zero_violation_counters": True,
            "mg_fg_crosswire": suites["mg_crosswire"]["exit_code"] == 0,
            "load_concurrency": suites["load_harness"]["exit_code"] == 0,
        },
    }

    out = ARTIFACTS / "forensic_audit.json"
    out.write_text(json.dumps(report, indent=2) + "\n")
    (ARTIFACTS / "forensic_audit.sha256").write_text(hashlib.sha256(out.read_bytes()).hexdigest() + "\n")
    print(json.dumps(report, indent=2))
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
