"""CG crystallize/commit load harness — correctness under concurrency."""
from __future__ import annotations

import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from statistics import median, quantiles

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parents[2]
SIDECAR = ROOT / "spine" / "sidecar"
sys.path.insert(0, str(SIDECAR))
sys.path.insert(0, str(ROOT))

from support.cyber_fixtures import EGRESS_PLATFORM, egress_facets

SCHEMA_SQL = (Path(__file__).parent.parent / "schema_sqlite.sql").read_text()
REPORTS_DIR = Path(__file__).parent / "reports"
_DEFAULT_WORKERS = "8" if os.environ.get("POSTGRES_TEST_URL") else "1"
_WORKERS = int(os.environ.get("LOAD_WORKERS", _DEFAULT_WORKERS))
_OPS = int(os.environ.get("LOAD_OPS_PER_WORKER", "5"))


def _bootstrap(engine) -> sessionmaker:
    with engine.begin() as conn:
        for stmt in SCHEMA_SQL.split(";"):
            s = stmt.strip()
            if s:
                conn.execute(text(s))
    from app.config import Settings, override_settings
    from app.db import override_engine
    from app.guardrails import reset_guardrails

    reset_guardrails()
    override_settings(
        Settings(
            database_url=str(engine.url),
            redis_url="redis://localhost:9/0",
            cg_internal_tokens="test-token",
            guardrails_enabled=False,
        )
    )
    override_engine(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def _crystallize_commit(worker: int, op: int) -> tuple[float, str]:
    from app.commit_ledger import commit_operation, crystallize_operation
    from app.config import get_settings
    from app.db import get_session_factory

    op_id = f"load-w{worker}-o{op}"
    facets = egress_facets(flow_id=op_id)
    start = time.perf_counter()
    session = get_session_factory()()
    try:
        c = crystallize_operation(
            session,
            get_settings(),
            platform=EGRESS_PLATFORM,
            operation_id=op_id,
            account_id="tenant-default",
            risk_tier="standard",
            facets=facets,
        )
        commit_operation(session, crystal_id=c.crystal_id, facets=facets, committed_budget=Decimal("0"))
        status = "ok"
    except Exception as exc:
        status = f"err:{exc}"
    finally:
        session.close()
    return time.perf_counter() - start, status


def _run_harness() -> dict:
    url = os.environ.get("POSTGRES_TEST_URL")
    if url:
        engine = create_engine(url, future=True, pool_size=_WORKERS, max_overflow=_WORKERS)
    else:
        engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            future=True,
        )
    _bootstrap(engine)

    from app.security_ops import assert_security_ops_invariants
    from app.db import get_db_session

    latencies: list[float] = []
    errors = 0
    with ThreadPoolExecutor(max_workers=_WORKERS) as pool:
        futures = [
            pool.submit(_crystallize_commit, w, o) for w in range(_WORKERS) for o in range(_OPS)
        ]
        for fut in as_completed(futures):
            elapsed, status = fut.result()
            latencies.append(elapsed)
            if status != "ok":
                errors += 1

    with get_db_session() as session:
        violations = 0
        try:
            assert_security_ops_invariants(session)
        except Exception:
            violations = 1

    latencies.sort()
    p95 = quantiles(latencies, n=20)[18] if len(latencies) >= 20 else latencies[-1]
    report = {
        "scenario": "crystallize_commit",
        "workers": _WORKERS,
        "ops_per_worker": _OPS,
        "total_ops": len(latencies),
        "errors": errors,
        "invariant_violations": violations,
        "p50_ms": median(latencies) * 1000,
        "p95_ms": p95 * 1000,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORTS_DIR / f"crystallize_commit_{int(time.time())}.json"
    out.write_text(json.dumps(report, indent=2))
    return report


def test_load_harness_zero_invariants():
    report = _run_harness()
    assert report["invariant_violations"] == 0
    assert report["errors"] == 0


if __name__ == "__main__":
    print(json.dumps(_run_harness(), indent=2))
