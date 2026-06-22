#!/usr/bin/env python3
from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.load.test_load_harness import run_reserve_hotpath_harness


def main() -> int:
    parser = ArgumentParser(description="Generate reserve hot-path invariant report")
    parser.add_argument("--operations", type=int, default=120)
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument(
        "--output",
        default=str(REPO_ROOT / "artifacts" / "reliability" / "latest_invariant_report.json"),
    )
    args = parser.parse_args()

    report = run_reserve_hotpath_harness(
        output_path=Path(args.output),
        operations=args.operations,
        workers=args.workers,
    )
    invariant_status = "PASS" if all(report["invariants"].values()) else "FAIL"
    print(f"invariant report: {args.output} ({invariant_status})")
    return 0 if invariant_status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
