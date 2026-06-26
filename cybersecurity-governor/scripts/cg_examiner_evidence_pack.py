#!/usr/bin/env python3
"""Generate examiner / diligence evidence pack for Cybersecurity Governor L4 Gold."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts" / "certification"
DOCS = ROOT.parent / "docs" / "cybersecurity-governor"


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
                "cybersecurity-governor/tests/",
                "--collect-only",
                "-q",
            ],
            cwd=ROOT.parent,
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
        "security_enforcement_mesh": str(DOCS / "security-enforcement-mesh.md"),
        "operations_runbook": str(DOCS / "operations-runbook.md"),
        "l4_certification": str(DOCS / "l4-certification.md"),
        "soc2_evidence_pack": str(DOCS / "soc2-evidence-pack.md"),
        "helm_chart": str(ROOT.parent / "deploy/helm/cybersecuritygovernor/Chart.yaml"),
        "argocd_application": str(
            ROOT.parent / "deploy/argocd/application-cybersecuritygovernor-production-helm.yaml"
        ),
        "certification_program": str(ROOT / "certification/program.yaml"),
    }
    body = {
        "pack_id": "cg-examiner-evidence-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_commit(),
        "automated_test_count": _test_count(),
        "chain_verify_endpoint": "/internal/security/verify-chain",
        "crystal_reconstruct_endpoint": "/internal/crystals/{crystal_id}/reconstruct",
        "certification_targets": {
            "institutional_plus_plus": "make cg-certification",
            "strict_l4_gold": "make cg-certification-strict",
            "l4_gold_ci": "make cg-certification-l4-ci",
            "l4_gold_full": "make cg-certification-l4",
        },
        "regulatory_export_endpoint": "/internal/regulatory/export",
        "artifact_references": {k: {"path": v, "exists": Path(v).is_file()} for k, v in refs.items()},
        "spine_invariant_counters": [
            "surprise_commit_blocked_total",
            "crystal_fingerprint_mismatch_total",
            "crystal_horizon_strand_total",
            "crystal_mesh_block_total",
            "security_chain_verification_failed_total",
            "negative_balance_detected_total",
            "stranded_without_hold_total",
        ],
        "platform_invariant_counters": {
            "egress_govern": ["egress_denied_total", "egress_allowlisted_total"],
            "threat_proxy": ["threat_blocked_total", "threat_cleared_total"],
            "posture_reconcile": ["posture_drift_total", "posture_matched_total"],
        },
        "security_mesh_rules": 7,
        "security_ops_probes": 7,
    }
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
    body["pack_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    return body


def main() -> int:
    pack = build_pack()
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = ARTIFACTS / f"cg-examiner-evidence-{stamp}.json"
    out.write_text(json.dumps(pack, indent=2, sort_keys=True) + "\n")
    missing = [k for k, v in pack["artifact_references"].items() if not v["exists"]]
    print(json.dumps({"path": str(out), "missing": missing, "pack_sha256": pack["pack_sha256"]}, indent=2))
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
