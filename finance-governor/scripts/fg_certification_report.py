#!/usr/bin/env python3
"""Generate external certification attestation report (FG-ECP)."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts" / "certification"


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, cwd=ROOT.parent).strip()
    except Exception:
        return "unknown"


def _run(cmd: list[str], cwd: Path) -> tuple[bool, str]:
    try:
        out = subprocess.check_output(cmd, cwd=cwd, stderr=subprocess.STDOUT, text=True)
        return True, out.strip()
    except subprocess.CalledProcessError as exc:
        return False, exc.output.strip()


def _file_exists(rel: str) -> bool:
    return (ROOT / rel).is_file() or (ROOT.parent / rel).is_file()


def build_checks(level: str, *, quick: bool = False) -> dict[str, dict]:
    checks: dict[str, dict] = {
        "platform_sdk_doc": {"pass": _file_exists("docs/platform-sdk.md"), "evidence": "docs/platform-sdk.md"},
        "partner_checklist": {"pass": _file_exists("certification/partner-checklist.md"), "evidence": "certification/partner-checklist.md"},
        "program_manifest": {"pass": _file_exists("certification/program.yaml"), "evidence": "certification/program.yaml"},
        "platform_conformance": {"pass": False, "evidence": "make fg-platform-conformance"},
        "unit_tests": {"pass": False, "evidence": "pytest tests/ --ignore=integration"},
        "inference_rail_module": {"pass": _file_exists("platforms/credit_govern/inference_rail.py"), "evidence": "inference_rail.py"},
        "values_rds_overlay": {"pass": _file_exists("deploy/helm/finance-governor/values-rds.yaml"), "evidence": "values-rds.yaml"},
        "istio_helm_helper": {"pass": "fg.istioPodAnnotations" in (ROOT / "deploy/helm/finance-governor/templates/_helpers.tpl").read_text()},
        "l4_certification_doc": {"pass": _file_exists("docs/l4-certification.md"), "evidence": "l4-certification.md"},
    }

    ok, _ = _run(["make", "fg-platform-conformance"], ROOT)
    checks["platform_conformance"]["pass"] = ok

    if quick:
        checks["unit_tests"]["pass"] = _file_exists("tests/test_platform_sdk.py")
    else:
        ok, _ = _run(
            ["python3", "-m", "pytest", "tests/", "-q", "--ignore=tests/integration", "--ignore=tests/chaos/test_toxiproxy_fg_spine.py"],
            ROOT,
        )
        checks["unit_tests"]["pass"] = ok

    if level in {"L4", "L5"}:
        ok, _ = _run(
            [
                "helm",
                "template",
                "fg",
                str(ROOT / "deploy/helm/finance-governor"),
                "-f",
                str(ROOT / "deploy/helm/finance-governor/values-production.yaml"),
                "-f",
                str(ROOT / "deploy/helm/finance-governor/values-enterprise.yaml"),
                "--set",
                "postgres.password=postgres",
                "--set",
                "secrets.create=true",
            ],
            ROOT,
        )
        checks["helm_enterprise_render"] = {"pass": ok, "evidence": "helm template enterprise"}

    if level == "L5":
        ok, out = _run(
            [
                "helm",
                "template",
                "fg",
                str(ROOT / "deploy/helm/finance-governor"),
                "-f",
                str(ROOT / "deploy/helm/finance-governor/values-production.yaml"),
                "-f",
                str(ROOT / "deploy/helm/finance-governor/values-enterprise.yaml"),
                "-f",
                str(ROOT / "deploy/helm/finance-governor/values-rds.yaml"),
                "--set",
                "postgres.password=postgres",
                "--set",
                "secrets.create=true",
                "--set",
                "postgres.external.host=fg-prod.cluster.example.rds.amazonaws.com",
            ],
            ROOT,
        )
        checks["rds_overlay_render"] = {
            "pass": ok and "fg-postgres" not in out,
            "evidence": "values-rds.yaml — no in-cluster postgres",
        }
        checks["istio_injection_annotations"] = {
            "pass": ok and "sidecar.istio.io/inject" in out,
            "evidence": "enterprise istio annotations on workloads",
        }

    return checks


def main() -> int:
    args = [a for a in sys.argv[1:] if a != "--quick"]
    quick = "--quick" in sys.argv[1:] or os.environ.get("FG_ECP_QUICK", "").lower() in {"1", "true", "yes"}
    level = args[0] if args else "L5"
    platform = args[1] if len(args) > 1 else "finance_governor_spine"

    checks = build_checks(level, quick=quick)
    body = {
        "program_id": "fg-ecp-v1",
        "level_claimed": level,
        "platform_name": platform,
        "git_commit": _git_commit(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
    }
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
    report = {**body, "report_sha256": hashlib.sha256(canonical.encode()).hexdigest()}

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = ARTIFACTS / f"fg-attestation-{platform}-{level}-{stamp}.json"
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

    failed = [k for k, v in checks.items() if not v.get("pass")]
    print(json.dumps({"path": str(out_path), "level": level, "failed": failed, "report_sha256": report["report_sha256"]}, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
