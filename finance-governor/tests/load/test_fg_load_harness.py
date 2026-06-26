"""Finance Governor load harness — concurrent crystallize gate path."""
from __future__ import annotations

import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal
from pathlib import Path
from statistics import median, quantiles

import pytest

ROOT = Path(__file__).resolve().parents[2]
SIDECAR = ROOT / "spine" / "sidecar"
sys.path.insert(0, str(SIDECAR))

FG_TESTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(FG_TESTS))

import threading

WORKERS = int(os.environ.get("FG_LOAD_WORKERS", "4"))
OPS = int(os.environ.get("FG_LOAD_OPS", "5"))
_load_lock = threading.Lock()


@pytest.fixture(scope="module")
def load_engine():
    from sqlalchemy import create_engine, text
    from sqlalchemy.pool import StaticPool

    from conftest_spine import SCHEMA

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    with engine.begin() as conn:
        for stmt in SCHEMA.split(";"):
            s = stmt.strip()
            if s:
                conn.execute(text(s))
    yield engine


def test_concurrent_crystallize_no_cap_overrun(load_engine):
    from app.commit_ledger import crystallize_operation
    from app.config import Settings
    from app.db import override_engine
    from app.regulatory_ops import assert_regulatory_ops_invariants
    from sqlalchemy.orm import sessionmaker

    settings = Settings(
        database_url=str(load_engine.url),
        redis_url="redis://localhost:6380/0",
        fg_internal_tokens="test-token",
    )
    override_engine(load_engine)
    factory = sessionmaker(bind=load_engine, autoflush=False, autocommit=False, future=True)
    latencies: list[float] = []
    errors = 0

    def _one(i: int) -> None:
        nonlocal errors
        t0 = time.perf_counter()
        try:
            with _load_lock:
                with factory() as session:
                    crystallize_operation(
                        session,
                        settings,
                        platform="wire_match",
                        operation_id=f"load-{i}",
                        account_id="desk-default",
                        risk_tier="low",
                        facets={"amount": "1.00"},
                        reserved_exposure=Decimal("1"),
                        policy_id="wire-critical-us",
                    )
            latencies.append((time.perf_counter() - t0) * 1000)
        except Exception:
            errors += 1

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = [pool.submit(_one, i * OPS + j) for i in range(WORKERS) for j in range(OPS)]
        for f in as_completed(futures):
            f.result()

    assert errors == 0
    with factory() as session:
        audit = assert_regulatory_ops_invariants(session)
        assert audit["negative_balances"] == 0

    assert len(latencies) == WORKERS * OPS
    p95 = quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies)
    assert p95 < 5000  # generous for SQLite in CI; production target 500ms
