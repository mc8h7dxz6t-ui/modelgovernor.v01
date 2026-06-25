#!/usr/bin/env python3
"""Generate Insurance Governor invariant report artifact."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT.parent / "artifacts" / "reliability" / "insurance-governor"


def main() -> int:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    env = {
        **os.environ,
        "PYTHONPATH": f"{ROOT.parent}/insurance-governor/spine/sidecar:{ROOT.parent}/insurance-governor",
    }
    tier1 = subprocess.run(
        [sys.executable, "-m", "pytest", "insurance-governor/tests/", "-q", "--ignore=insurance-governor/tests/load"],
        cwd=ROOT.parent,
        capture_output=True,
        text=True,
        env=env,
    )
    load = subprocess.run(
        [sys.executable, "-m", "pytest", "insurance-governor/tests/load/test_ig_load_harness.py", "-q"],
        cwd=ROOT.parent,
        capture_output=True,
        text=True,
        env=env,
    )
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tier1_exit_code": tier1.returncode,
        "tier1_stdout": tier1.stdout[-2000:],
        "load_exit_code": load.returncode,
        "load_stdout": load.stdout[-2000:],
        "certification": tier1.returncode == 0 and load.returncode == 0,
    }
    out = ARTIFACTS / f"ig_invariant_report_{int(datetime.now().timestamp())}.json"
    out.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    return 0 if report["certification"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
