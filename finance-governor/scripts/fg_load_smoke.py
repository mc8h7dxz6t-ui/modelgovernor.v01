#!/usr/bin/env python3
"""Finance Governor load smoke — concurrent crystallize/commit against sidecar."""
from __future__ import annotations

import argparse
import concurrent.futures
import os
import sys
import uuid

import httpx

SIDECAR = os.environ.get("FG_SIDECAR_URL", "http://localhost:8091")
TOKEN = os.environ.get("FG_INTERNAL_TOKEN", "dev-fg-spine-token-change-me")
HEADERS = {"x-internal-token": TOKEN, "content-type": "application/json"}


def one_op(worker_id: int) -> tuple[bool, str]:
    op_id = f"load-{worker_id}-{uuid.uuid4().hex[:8]}"
    facets = {"amount": "1.00", "worker": worker_id}
    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.post(
                f"{SIDECAR}/crystallize",
                headers=HEADERS,
                json={
                    "platform": "wire_match",
                    "operation_id": op_id,
                    "risk_tier": "standard",
                    "facets": facets,
                },
            )
            r.raise_for_status()
            crystal_id = r.json()["crystal_id"]
            c = client.post(
                f"{SIDECAR}/commit",
                headers=HEADERS,
                json={"crystal_id": crystal_id, "facets": facets, "committed_exposure": "0"},
            )
            c.raise_for_status()
        return True, op_id
    except Exception as exc:
        return False, f"{op_id}: {exc}"


def main() -> int:
    parser = argparse.ArgumentParser(description="FG load smoke")
    parser.add_argument("--workers", type=int, default=int(os.environ.get("FG_LOAD_WORKERS", "8")))
    parser.add_argument("--ops", type=int, default=int(os.environ.get("FG_LOAD_OPS", "5")))
    args = parser.parse_args()

    total = args.workers * args.ops
    failures: list[str] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(one_op, i) for i in range(total)]
        for fut in concurrent.futures.as_completed(futures):
            ok, msg = fut.result()
            if not ok:
                failures.append(msg)

    print(f"fg_load_smoke: {total - len(failures)}/{total} ok")
    if failures:
        for f in failures[:5]:
            print(f"  FAIL {f}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
