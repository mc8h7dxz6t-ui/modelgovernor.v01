#!/usr/bin/env python3
"""Generate examiner / diligence evidence pack for FG-ECP L5."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts" / "certification"
DOCS = ROOT.parent / "docs" / "finance-governor"


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, cwd=ROOT.parent).strip()
    except Exception:
        return "unknown"


def _test_count() -> int:
    try:
        out = subprocess.check_output(
            [
                "python3",
                "-m",
                "pytest",
                "tests/",
                "--collect-only",
                "-q",
            ],
            cwd=ROOT,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        for line in out.splitlines():
            if " test" in line and " collected" in line:
                return int(line.split()[0])
    except Exception:
        pass
    return 0


def build_pack() -> dict:
    refs = {
        "capability_matrix": str(DOCS / "capability-matrix.md"),
        "institutional_gold_standard": str(DOCS / "institutional-gold-standard.md"),
        "soc2_evidence_pack": str(DOCS / "soc2-evidence-pack.md"),
        "design_partner_program": str(DOCS / "design-partner-program.md"),
        "l4_certification": str(ROOT / "docs/l4-certification.md"),
        "external_certification": str(ROOT / "docs/external-certification.md"),
        "program_manifest": str(ROOT / "certification/program.yaml"),
        "argocd_application": str(ROOT / "deploy/argocd/application-production.yaml"),
    }
    body = {
        "pack_id": "fg-examiner-evidence-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_commit(),
        "automated_test_count": _test_count(),
        "regulatory_export_endpoint": "/internal/regulatory/export",
        "chain_verify_endpoint": "/internal/decisions/verify-chain",
        "certification_targets": {
            "institutional_plus_plus": "make fg-certification",
            "l4_gold": "make fg-certification-l4",
            "l5_industry_leading": "make fg-certification-external-full",
        },
        "artifact_references": {k: {"path": v, "exists": Path(v).is_file()} for k, v in refs.items()},
        "invariant_counters": [
            "surprise_commit_blocked_total",
            "crystal_fingerprint_mismatch_total",
            "crystal_horizon_strand_total",
            "reconciler_horizon_strand_total",
            "ledger_chain_verification_failed_total",
        ],
    }
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
    body["pack_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    return body


def main() -> int:
    pack = build_pack()
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = ARTIFACTS / f"fg-examiner-evidence-{stamp}.json"
    out.write_text(json.dumps(pack, indent=2, sort_keys=True) + "\n")
    missing = [k for k, v in pack["artifact_references"].items() if not v["exists"]]
    print(json.dumps({"path": str(out), "missing": missing, "pack_sha256": pack["pack_sha256"]}, indent=2))
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
