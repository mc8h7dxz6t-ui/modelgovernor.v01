#!/usr/bin/env python3
from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.load.test_load_harness import run_all_scenarios


def main() -> int:
    parser = ArgumentParser(description="Generate load-harness invariant report")
    parser.add_argument(
        "--output",
        default=str(REPO_ROOT / "artifacts" / "reliability" / "latest_invariant_report.json"),
        help="Legacy output path; report is written by run_all_scenarios to tests/load/reports/",
    )
    args = parser.parse_args()

    summary = run_all_scenarios()
    report_path = Path(summary["report_path"])
    violations = sum(
        int(scenario.get("invariant_violations", 0)) for scenario in summary["results"]
    )
    status = "PASS" if violations == 0 else "FAIL"

    legacy_path = Path(args.output)
    legacy_path.parent.mkdir(parents=True, exist_ok=True)
    legacy_path.write_text(report_path.read_text(encoding="utf-8"), encoding="utf-8")

    print(f"invariant report: {report_path} ({status})")
    print(f"legacy copy: {legacy_path}")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
