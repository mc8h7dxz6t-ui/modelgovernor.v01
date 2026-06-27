#!/usr/bin/env python3
"""Generate Cybersecurity Governor institutional attestation artifact."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
ARTIFACTS = REPO / "artifacts" / "reliability" / "cybersecurity-governor"


def _run(cmd: list[str], env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, env=env)


def _pytest(env: dict, *paths: str) -> subprocess.CompletedProcess:
    return _run([sys.executable, "-m", "pytest", *paths, "-q"], env)


def main() -> int:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    env = {
        **os.environ,
        "PYTHONPATH": (
            f"{REPO}/cybersecurity-governor/spine/sidecar:"
            f"{REPO}/cybersecurity-governor/tests:"
            f"{REPO}/cybersecurity-governor"
        ),
    }
    tier1 = _run(
        [
            sys.executable,
            "-m",
            "pytest",
            "cybersecurity-governor/tests/",
            "-q",
            "--ignore=cybersecurity-governor/tests/chaos",
            "--ignore=cybersecurity-governor/tests/load",
        ],
        env,
    )
    load = _pytest(env, "cybersecurity-governor/tests/load/test_cg_load_harness.py")
    platform_tests = _pytest(
        env,
        "cybersecurity-governor/tests/test_cyber_platforms.py",
        "cybersecurity-governor/tests/test_security_mesh.py",
        "cybersecurity-governor/tests/test_platform_invariant_counters.py",
        "cybersecurity-governor/tests/test_platform_sdk.py",
    )
    l4_artifacts = _pytest(env, "cybersecurity-governor/tests/test_l4_artifacts_present.py")
    l4_runtime = _pytest(env, "cybersecurity-governor/tests/test_l4_runtime_enforcement.py")
    helm = _run(
        [
            "helm",
            "template",
            "cg",
            "deploy/helm/cybersecuritygovernor",
            "-f",
            "deploy/helm/cybersecuritygovernor/values-production.yaml",
            "-f",
            "deploy/helm/cybersecuritygovernor/values-enterprise.yaml",
            "--set",
            "secrets.create=true",
            "--set",
            "secrets.postgresPassword=postgres",
        ],
        env,
    )
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "certification_level": "L4_GOLD",
        "framing": "institutional test + deploy kit gate — not a Fortune 500 cyber product claim",
        "platforms": [
            "egress_govern",
            "identity_govern",
            "threat_proxy",
            "incident_response_gate",
            "posture_reconcile",
            "compliance_logger",
            "witness_bridge",
            "lineage_ingest",
            "content_guard",
        ],
        "tier1_exit_code": tier1.returncode,
        "tier1_summary": tier1.stdout.strip().splitlines()[-1] if tier1.stdout else "",
        "load_exit_code": load.returncode,
        "platform_tests_exit_code": platform_tests.returncode,
        "l4_artifacts_exit_code": l4_artifacts.returncode,
        "l4_runtime_exit_code": l4_runtime.returncode,
        "helm_template_exit_code": helm.returncode,
        "certification": all(
            proc.returncode == 0
            for proc in (tier1, load, platform_tests, l4_artifacts, l4_runtime, helm)
        ),
        "attestation": {
            "tier1_pytest_passed": tier1.returncode == 0,
            "load_harness_passed": load.returncode == 0,
            "platform_conformance_passed": platform_tests.returncode == 0,
            "l4_artifacts_present": l4_artifacts.returncode == 0,
            "l4_runtime_enforcement": l4_runtime.returncode == 0,
            "helm_deploy_kit_renders": helm.returncode == 0,
            "s3_object_lock_anchor_scaffold": (
                REPO / "deploy/infra/aws/security-anchor-bucket.yaml"
            ).is_file(),
        },
        "commercial": {
            "honest_pitch": "Tamper-evident authorization ledger for security commits",
            "defensible_wedge": "EgressGovern + mesh + chain verify + Envoy ext_authz adapter",
            "enforcement_wedges": [
                "egress_govern",
                "identity_govern",
                "witness_bridge",
                "lineage_ingest",
                "posture_reconcile",
                "content_guard",
                "threat_proxy",
                "incident_response_gate",
                "compliance_logger",
            ],
            "capability_matrix": "docs/cybersecurity-governor/capability-matrix.md",
            "security_mesh_doc": "docs/cybersecurity-governor/security-enforcement-mesh.md",
        },
    }
    ts = int(datetime.now(timezone.utc).timestamp())
    out = ARTIFACTS / f"cg_attestation_{ts}.json"
    latest = ARTIFACTS / "latest_attestation.json"
    payload = json.dumps(report, indent=2)
    out.write_text(payload)
    latest.write_text(payload)

    cluster_path = ARTIFACTS / "cluster_attestation.json"
    cert_hash = hashlib.sha256(payload.encode()).hexdigest()
    if cluster_path.is_file():
        cluster_report = json.loads(cluster_path.read_text())
        if int(cluster_report.get("probes_total") or 0) > 0:
            cluster_report["certification_sha256"] = cert_hash
            cluster_report["certification_bundled"] = report["certification"]
            cluster_path.write_text(json.dumps(cluster_report, indent=2))

    print(payload)
    return 0 if report["certification"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
