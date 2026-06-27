"""External certification (FG-ECP) attestation tests."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_program_manifest_exists():
    assert (ROOT / "certification/program.yaml").is_file()


def test_partner_checklist_exists():
    assert (ROOT / "certification/partner-checklist.md").is_file()


def test_external_certification_doc_exists():
    assert (ROOT / "docs/external-certification.md").is_file()


def test_attestation_report_generates_l5():
    env = {**os.environ, "FG_ECP_QUICK": "1"}
    result = subprocess.run(
        ["python3", "scripts/fg_certification_report.py", "--quick", "L5", "finance_governor"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["level"] == "L5"
    assert not payload["failed"]
    report_path = Path(payload["path"])
    assert report_path.is_file()
    report = json.loads(report_path.read_text())
    assert report["program_id"] == "fg-ecp-v1"
    assert report["report_sha256"]
    assert all(v["pass"] for v in report["checks"].values())
