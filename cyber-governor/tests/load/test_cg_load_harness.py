"""Tier 3 — load harness (institutional++ gate).

Run: CG_LOAD_TEST=1 pytest tests/load/test_cg_load_harness.py -v -s
"""
from __future__ import annotations

import os
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pytest

from tests.helpers import cg_settings, create_sqlite_engine, identity_facets, session_factory

pytestmark = pytest.mark.skipif(
    os.environ.get("CG_LOAD_TEST") != "1",
    reason="Set CG_LOAD_TEST=1 to run load harness",
)

TARGET_RPS = int(os.environ.get("CG_LOAD_RPS", "50"))
DURATION_SEC = float(os.environ.get("CG_LOAD_DURATION", "3"))
WORKERS = int(os.environ.get("CG_LOAD_WORKERS", "8"))


def _one_crystallize_commit(settings, engine, idx: int) -> float:
    from app.commit_ledger import commit_operation, crystallize_operation

    t0 = time.perf_counter()
    facets = identity_facets(worker=idx)
    Session = session_factory(engine)
    with Session() as s:
        cr = crystallize_operation(
            s,
            settings,
            platform="identity_gate",
            operation_id=f"load-{idx}-{int(t0 * 1e6)}",
            account_id="tenant-default",
            risk_tier="critical",
            facets=facets,
            policy_id="identity-critical-us",
        )
        crystal_id = cr.crystal_id
    with Session() as s:
        commit_operation(s, crystal_id=crystal_id, facets=facets, outcome="authorized")
    return time.perf_counter() - t0


@pytest.fixture()
def load_engine(tmp_path):
    from app.db import override_engine

    eng = create_sqlite_engine(tmp_path / "load.sqlite3")
    override_engine(eng)
    yield eng


def test_crystallize_commit_load_harness(load_engine):
    from app.security_seal import verify_security_chain

    settings = cg_settings(str(load_engine.url))
    target_ops = int(TARGET_RPS * DURATION_SEC)
    latencies: list[float] = []
    errors = 0
    t_start = time.perf_counter()
    idx = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = []
        while idx < target_ops and (time.perf_counter() - t_start) < DURATION_SEC:
            futures.append(pool.submit(_one_crystallize_commit, settings, load_engine, idx))
            idx += 1
            if len(futures) >= WORKERS * 2:
                for f in as_completed(futures[:WORKERS]):
                    try:
                        latencies.append(f.result())
                    except Exception:
                        errors += 1
                futures = futures[WORKERS:]
        for f in as_completed(futures):
            try:
                latencies.append(f.result())
            except Exception:
                errors += 1

    elapsed = time.perf_counter() - t_start
    achieved_rps = len(latencies) / max(elapsed, 0.001)
    p50 = statistics.median(latencies) * 1000 if latencies else 9999
    p99 = (sorted(latencies)[int(len(latencies) * 0.99)] * 1000) if len(latencies) > 10 else 9999

    Session = session_factory(load_engine)
    with Session() as s:
        report = verify_security_chain(s)
    assert report.valid is True
    assert errors == 0, f"load errors={errors}"
    assert achieved_rps >= TARGET_RPS * 0.5, (
        f"achieved_rps={achieved_rps:.1f} target_floor={TARGET_RPS * 0.5}"
    )
    assert p99 < 5000, f"p99_ms={p99:.1f}"

    print(
        f"\nLOAD: ops={len(latencies)} rps={achieved_rps:.1f} "
        f"p50_ms={p50:.1f} p99_ms={p99:.1f} workers={WORKERS}"
    )
