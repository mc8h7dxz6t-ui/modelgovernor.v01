"""Reproducible load / benchmark harness for the ledger reserve hot path.

This module can be run directly as a script or collected by pytest.  It
exercises three scenarios:

  1. hot-trace contention — all workers share the same trace, cap set to allow
     roughly half of them to succeed.
  2. distributed contention — each worker has its own trace; all should succeed.
  3. mixed activity — reserve, timeout, settle, and reconciler sweep running
     concurrently.

The harness captures p50 / p95 / p99 latency for the reserve path, counts
invariant violations, and writes a JSON report artifact to
``tests/load/reports/<scenario>_<timestamp>.json``.

Usage
-----
Run against SQLite (fast, always available)::

    python tests/load/test_load_harness.py

Run against Postgres (institutional proof)::

    POSTGRES_TEST_URL=postgresql+psycopg://postgres:postgres@localhost:5432/mg_test python tests/load/test_load_harness.py

Run as pytest targets::

    pytest tests/load/test_load_harness.py -v

Configuration via environment variables
-----------------------------------------
``POSTGRES_TEST_URL``
    Postgres DSN.  When set, Postgres is used; otherwise SQLite in /tmp.
``LOAD_WORKERS``
    Number of concurrent worker threads (default: 20).
``LOAD_OPS_PER_WORKER``
    Operations per worker per scenario (default: 25).
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from statistics import median, quantiles
from tempfile import mkstemp
from typing import Any

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

sqlite3.register_adapter(Decimal, lambda v: str(v))

from reconciler.app.sweeper import sweep_expired_reservations
from sidecar.app.config import Settings
from sidecar.app.ledger import (
    TraceCapExceededError,
    apply_settlement,
    reserve_operation,
)
from sidecar.app.metrics import get_counters
from sidecar.app.schemas import ReserveRequest, SettleRequest

REPORTS_DIR = Path(__file__).parent / "reports"
MONEY_QUANTUM = Decimal("0.000001")

_WORKERS = int(os.environ.get("LOAD_WORKERS", "20"))
_OPS = int(os.environ.get("LOAD_OPS_PER_WORKER", "25"))


# ---------------------------------------------------------------------------
# Engine helpers
# ---------------------------------------------------------------------------

def _make_sqlite_engine():
    _, path = mkstemp(suffix=".sqlite3", prefix="mg_load_")
    engine = create_engine(
        f"sqlite:///{path}",
        future=True,
        connect_args={"check_same_thread": False},
    )
    with engine.begin() as conn:
        conn.execute(text("PRAGMA journal_mode=WAL"))
    _bootstrap_sqlite(engine)
    return engine


def _make_postgres_engine(url: str):
    engine = create_engine(url, future=True, pool_size=_WORKERS, max_overflow=_WORKERS)
    _apply_pg_migrations(engine)
    return engine


def _make_engine():
    pg_url = os.environ.get("POSTGRES_TEST_URL")
    if pg_url:
        return "postgres", _make_postgres_engine(pg_url)
    return "sqlite", _make_sqlite_engine()


def _make_settings(engine) -> Settings:
    return Settings(
        database_url=str(engine.url),
        redis_url="redis://example/0",
        sidecar_internal_tokens="load-test-token",
        reserve_ttl_seconds=300,
        default_trace_cap_amount=Decimal("5000"),
        drift_absolute_tolerance=Decimal("1.000000"),
        drift_ratio_tolerance=Decimal("0.200000"),  # relaxed for load tests
        db_pool_size=_WORKERS,
        db_max_overflow=_WORKERS,
        db_pool_timeout_seconds=10,
        db_pool_recycle_seconds=300,
    )


# ---------------------------------------------------------------------------
# Latency measurement
# ---------------------------------------------------------------------------

@dataclass
class LatencySample:
    scenario: str
    outcome: str
    duration_ms: float


def _pct(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    idx = max(0, int(len(sorted_vals) * p / 100) - 1)
    return sorted_vals[min(idx, len(sorted_vals) - 1)]


def _summarise(samples: list[LatencySample]) -> dict[str, Any]:
    durations = sorted(s.duration_ms for s in samples)
    outcomes: dict[str, int] = {}
    for s in samples:
        outcomes[s.outcome] = outcomes.get(s.outcome, 0) + 1
    return {
        "n": len(samples),
        "outcomes": outcomes,
        "latency_ms": {
            "p50": round(_pct(durations, 50), 2),
            "p95": round(_pct(durations, 95), 2),
            "p99": round(_pct(durations, 99), 2),
            "min": round(min(durations, default=0), 2),
            "max": round(max(durations, default=0), 2),
        },
    }


# ---------------------------------------------------------------------------
# Scenario 1: Hot-trace contention
# ---------------------------------------------------------------------------

def _run_hot_trace_contention(engine, settings: Settings, n_workers: int) -> dict:
    """All workers attempt reserves against ONE trace with a tight cap.

    Cap = n_workers * cost / 2 so exactly ~half succeed.
    Proves atomic cap enforcement under maximum contention.
    """
    get_counters().reset()
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    cost = Decimal("4")
    cap = cost * (n_workers // 2)

    # Patch a tighter cap onto a fresh trace via settings override.
    tight_settings = Settings(
        database_url=settings.database_url,
        redis_url=settings.redis_url,
        sidecar_internal_tokens=settings.sidecar_internal_tokens,
        reserve_ttl_seconds=settings.reserve_ttl_seconds,
        default_trace_cap_amount=cap,
        drift_absolute_tolerance=settings.drift_absolute_tolerance,
        drift_ratio_tolerance=settings.drift_ratio_tolerance,
        db_pool_size=settings.db_pool_size,
        db_max_overflow=settings.db_max_overflow,
        db_pool_timeout_seconds=settings.db_pool_timeout_seconds,
        db_pool_recycle_seconds=settings.db_pool_recycle_seconds,
    )

    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO user_wallets (user_id, balance, active) "
                "VALUES ('ht-user', 100000, TRUE) "
                + ("ON CONFLICT DO NOTHING" if "sqlite" in str(engine.url) else "ON CONFLICT (user_id) DO NOTHING")
            )
        )

    samples: list[LatencySample] = []
    invariant_violations = 0

    def worker(i: int) -> LatencySample:
        key = f"ht-op-{i}"
        t0 = time.perf_counter()
        with factory() as s:
            try:
                reserve_operation(
                    s,
                    tight_settings,
                    ReserveRequest(
                        user_id="ht-user",
                        trace_id="ht-trace",
                        idempotency_key=key,
                        model="gpt-4o-mini",
                        estimated_cost=cost,
                    ),
                )
                outcome = "reserved"
            except TraceCapExceededError:
                s.rollback()
                outcome = "cap_exceeded"
            except Exception as exc:
                s.rollback()
                outcome = f"error:{exc}"
        elapsed_ms = (time.perf_counter() - t0) * 1000
        return LatencySample(scenario="hot_trace", outcome=outcome, duration_ms=elapsed_ms)

    with ThreadPoolExecutor(max_workers=n_workers) as pool:
        samples = list(pool.map(worker, range(n_workers)))

    # Invariant: reserved_total must not exceed cap
    with Session(engine) as s:
        row = s.execute(
            text(
                "SELECT reserved_total, cap_amount FROM trace_budget_state "
                "WHERE trace_id = 'ht-trace'"
            )
        ).mappings().first()
        if row and Decimal(str(row["reserved_total"])) > Decimal(str(row["cap_amount"])):
            invariant_violations += 1

    summary = _summarise(samples)
    summary["invariant_violations"] = invariant_violations
    summary["scenario"] = "hot_trace_contention"
    summary["metrics"] = get_counters().snapshot()
    return summary


# ---------------------------------------------------------------------------
# Scenario 2: Distributed contention (many traces)
# ---------------------------------------------------------------------------

def _run_distributed_contention(engine, settings: Settings, n_workers: int) -> dict:
    """Each worker gets its own trace — no cap pressure, measures base latency."""
    get_counters().reset()
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO user_wallets (user_id, balance, active) "
                "VALUES ('dc-user', 100000, TRUE) "
                + ("ON CONFLICT DO NOTHING" if "sqlite" in str(engine.url) else "ON CONFLICT (user_id) DO NOTHING")
            )
        )

    samples: list[LatencySample] = []

    def worker(i: int) -> LatencySample:
        t0 = time.perf_counter()
        with factory() as s:
            try:
                reserve_operation(
                    s,
                    settings,
                    ReserveRequest(
                        user_id="dc-user",
                        trace_id=f"dc-trace-{i}",
                        idempotency_key=f"dc-op-{i}",
                        model="gpt-4o-mini",
                        estimated_cost=Decimal("3"),
                    ),
                )
                outcome = "reserved"
            except Exception as exc:
                s.rollback()
                outcome = f"error:{exc}"
        return LatencySample(
            scenario="distributed", outcome=outcome,
            duration_ms=(time.perf_counter() - t0) * 1000
        )

    with ThreadPoolExecutor(max_workers=n_workers) as pool:
        samples = list(pool.map(worker, range(n_workers)))

    summary = _summarise(samples)
    summary["scenario"] = "distributed_contention"
    summary["metrics"] = get_counters().snapshot()
    return summary


# ---------------------------------------------------------------------------
# Scenario 3: Mixed activity (reserve / timeout / settle / sweep)
# ---------------------------------------------------------------------------

def _run_mixed_activity(engine, settings: Settings, n_workers: int, ops: int) -> dict:
    """Concurrent mix of reserves, timeouts, settlements, and sweeps."""
    get_counters().reset()
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO user_wallets (user_id, balance, active) "
                "VALUES ('mx-user', 100000, TRUE) "
                + ("ON CONFLICT DO NOTHING" if "sqlite" in str(engine.url) else "ON CONFLICT (user_id) DO NOTHING")
            )
        )

    samples: list[LatencySample] = []

    def worker(i: int) -> list[LatencySample]:
        worker_samples = []
        for j in range(ops):
            key = f"mx-op-{i}-{j}"
            trace_id = f"mx-trace-{i}-{j}"

            # Reserve
            t0 = time.perf_counter()
            with factory() as s:
                try:
                    reserve_operation(
                        s,
                        settings,
                        ReserveRequest(
                            user_id="mx-user",
                            trace_id=trace_id,
                            idempotency_key=key,
                            model="gpt-4o-mini",
                            estimated_cost=Decimal("2"),
                        ),
                    )
                    outcome = "reserved"
                except Exception as exc:
                    s.rollback()
                    outcome = f"reserve_error:{exc}"
            worker_samples.append(LatencySample(
                scenario="mixed_reserve", outcome=outcome,
                duration_ms=(time.perf_counter() - t0) * 1000,
            ))
            if outcome != "reserved":
                continue

            # Alternate: settle immediately or let some expire (by index)
            if j % 3 == 0:
                # Expire path: back-date and let sweeper handle
                with engine.begin() as conn:
                    conn.execute(
                        text(
                            "UPDATE escrow_ledger SET expires_at = :t "
                            "WHERE idempotency_key = :k"
                        ),
                        {"t": datetime.now(timezone.utc) - timedelta(minutes=5), "k": key},
                    )
            else:
                # Settle path
                with factory() as s:
                    try:
                        apply_settlement(
                            s,
                            settings,
                            SettleRequest(
                                idempotency_key=key,
                                outcome="SETTLED",
                                actual_cost=Decimal("1.8"),
                                provider_request_id=f"prid-mx-{i}-{j}",
                            ),
                        )
                    except Exception:
                        s.rollback()

        return worker_samples

    with ThreadPoolExecutor(max_workers=n_workers) as pool:
        for batch in pool.map(worker, range(n_workers)):
            samples.extend(batch)

    # Run reconciler sweep to clean up expired rows
    with factory() as s:
        sweep_expired_reservations(s, batch_size=n_workers * ops)

    # Invariant: no negative balances
    invariant_violations = 0
    with Session(engine) as s:
        neg = s.execute(
            text("SELECT COUNT(*) FROM user_wallets WHERE balance < 0")
        ).scalar_one()
        invariant_violations += int(neg)

    summary = _summarise(samples)
    summary["scenario"] = "mixed_activity"
    summary["invariant_violations"] = invariant_violations
    summary["metrics"] = get_counters().snapshot()
    return summary


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------

def _write_report(results: list[dict], db_mode: str) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_path = REPORTS_DIR / f"load_report_{db_mode}_{ts}.json"
    report = {
        "generated_at": ts,
        "db_mode": db_mode,
        "workers": _WORKERS,
        "ops_per_worker": _OPS,
        "scenarios": results,
    }
    report_path.write_text(json.dumps(report, indent=2))
    return report_path


# ---------------------------------------------------------------------------
# Entry point (also usable from pytest)
# ---------------------------------------------------------------------------

def run_all_scenarios() -> dict:
    db_mode, engine = _make_engine()
    settings = _make_settings(engine)

    results = []
    print(f"\n[load_harness] db_mode={db_mode}  workers={_WORKERS}  ops/worker={_OPS}")

    for label, fn in [
        ("hot_trace_contention", lambda: _run_hot_trace_contention(engine, settings, _WORKERS)),
        ("distributed_contention", lambda: _run_distributed_contention(engine, settings, _WORKERS)),
        (
            "mixed_activity",
            lambda: _run_mixed_activity(engine, settings, _WORKERS, _OPS),
        ),
    ]:
        t0 = time.perf_counter()
        result = fn()
        elapsed = round((time.perf_counter() - t0) * 1000, 1)
        result["wall_ms"] = elapsed
        results.append(result)
        violations = result.get("invariant_violations", 0)
        lat = result.get("latency_ms", {})
        print(
            f"  {label}: "
            f"n={result['n']} "
            f"p50={lat.get('p50')}ms "
            f"p95={lat.get('p95')}ms "
            f"p99={lat.get('p99')}ms "
            f"violations={violations} "
            f"wall={elapsed}ms"
        )
        if violations:
            print(f"  *** INVARIANT VIOLATION in {label}: {violations} ***")

    report_path = _write_report(results, db_mode)
    print(f"\n[load_harness] report written to {report_path}")
    engine.dispose()

    return {
        "db_mode": db_mode,
        "results": results,
        "report_path": str(report_path),
    }


# ---------------------------------------------------------------------------
# pytest-visible tests — collected by pytest automatically
# ---------------------------------------------------------------------------

def test_load_hot_trace_contention_invariants() -> None:
    """Load test: hot-trace contention must produce zero invariant violations."""
    db_mode, engine = _make_engine()
    settings = _make_settings(engine)
    try:
        result = _run_hot_trace_contention(engine, settings, _WORKERS)
    finally:
        engine.dispose()

    assert result["invariant_violations"] == 0, (
        f"Invariant violated in hot-trace scenario: {result}"
    )
    # At least some operations should succeed and some should be denied.
    assert result["outcomes"].get("reserved", 0) >= 1
    assert result["outcomes"].get("cap_exceeded", 0) >= 1


def test_load_distributed_contention_all_succeed() -> None:
    """Load test: distributed traces — all reserve operations must succeed."""
    db_mode, engine = _make_engine()
    settings = _make_settings(engine)
    try:
        result = _run_distributed_contention(engine, settings, _WORKERS)
    finally:
        engine.dispose()

    errors = {k: v for k, v in result["outcomes"].items() if k.startswith("error:")}
    assert not errors, f"Errors in distributed scenario: {errors}"
    assert result["outcomes"].get("reserved", 0) == _WORKERS


def test_load_mixed_activity_no_negative_balances() -> None:
    """Load test: mixed reserve/settle/sweep activity leaves no negative balances."""
    db_mode, engine = _make_engine()
    settings = _make_settings(engine)
    try:
        result = _run_mixed_activity(engine, settings, _WORKERS, _OPS)
    finally:
        engine.dispose()

    assert result["invariant_violations"] == 0, (
        f"Negative balance detected in mixed scenario: {result}"
    )


# ---------------------------------------------------------------------------
# Bootstrap helpers (SQLite)
# ---------------------------------------------------------------------------

def _bootstrap_sqlite(engine) -> None:
    with engine.begin() as conn:
        conn.execute(text(
            """
            CREATE TABLE IF NOT EXISTS user_wallets (
                user_id TEXT PRIMARY KEY,
                balance NUMERIC(18,6) NOT NULL DEFAULT 100.000000,
                active BOOLEAN NOT NULL DEFAULT TRUE,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                locked_at TIMESTAMP,
                lock_reason TEXT
            )
            """
        ))
        conn.execute(text(
            """
            CREATE TABLE IF NOT EXISTS model_policy_registry (
                model_name TEXT PRIMARY KEY,
                provider TEXT NOT NULL,
                enabled BOOLEAN NOT NULL DEFAULT TRUE,
                max_input_tokens INTEGER NOT NULL,
                max_output_tokens INTEGER NOT NULL,
                max_cost_per_request NUMERIC(18,6) NOT NULL,
                stream_allowed BOOLEAN NOT NULL DEFAULT TRUE,
                fallback_price_per_token NUMERIC(18,6) NOT NULL,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        ))
        conn.execute(text(
            """
            CREATE TABLE IF NOT EXISTS escrow_ledger (
                idempotency_key TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                trace_id TEXT NOT NULL,
                model TEXT NOT NULL,
                request_fingerprint TEXT NOT NULL,
                reserved_amount NUMERIC(18,6) NOT NULL,
                actual_amount NUMERIC(18,6) NOT NULL DEFAULT 0.000000,
                status TEXT NOT NULL DEFAULT 'RESERVED',
                provider_request_id TEXT,
                terminal_reason TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                settled_at TIMESTAMP,
                expired_at TIMESTAMP,
                reconciled BOOLEAN NOT NULL DEFAULT FALSE,
                trace_cap_amount NUMERIC(18,6) NOT NULL DEFAULT 25.000000,
                dispatch_started_at TIMESTAMP,
                drift_amount NUMERIC(18,6) NOT NULL DEFAULT 0.000000
            )
            """
        ))
        conn.execute(text(
            """
            CREATE TABLE IF NOT EXISTS ledger_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                idempotency_key TEXT NOT NULL,
                user_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                amount_delta NUMERIC(18,6) NOT NULL,
                metadata TEXT NOT NULL DEFAULT '{}',
                recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        ))
        conn.execute(text(
            """
            CREATE TABLE IF NOT EXISTS trace_budget_state (
                trace_id TEXT PRIMARY KEY,
                cap_amount NUMERIC(18,6) NOT NULL,
                reserved_total NUMERIC(18,6) NOT NULL DEFAULT 0.000000,
                settled_total NUMERIC(18,6) NOT NULL DEFAULT 0.000000,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        ))
        conn.execute(text(
            """
            CREATE TABLE IF NOT EXISTS provider_dispatch_attempts (
                attempt_key TEXT PRIMARY KEY,
                idempotency_key TEXT NOT NULL,
                provider_name TEXT,
                model_name TEXT,
                provider_request_id TEXT UNIQUE,
                status TEXT NOT NULL,
                terminal_reason TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        ))
        conn.execute(text(
            """
            INSERT OR IGNORE INTO model_policy_registry
                (model_name, provider, enabled, max_input_tokens, max_output_tokens,
                 max_cost_per_request, stream_allowed, fallback_price_per_token)
            VALUES ('gpt-4o-mini', 'openai', TRUE, 128000, 4096, 5.0, TRUE, 0.00005)
            """
        ))


def _apply_pg_migrations(engine) -> None:
    migrations_dir = REPO_ROOT / "migrations"
    migration_files = [
        "0001_init.sql",
        "0002_seed_model_policy.sql",
        "0003_harden_ledger_constraints.sql",
        "0004_ledger_control_plane_hardening.sql",
        "0005_invariant_constraints.sql",
        "0006_execution_attribution_guardrails.sql",
    ]
    with engine.begin() as conn:
        for filename in migration_files:
            sql = (migrations_dir / filename).read_text()
            for stmt in sql.split(";"):
                stripped = stmt.strip()
                if stripped:
                    try:
                        conn.execute(text(stripped))
                    except Exception:
                        raise


if __name__ == "__main__":
    summary = run_all_scenarios()
    any_violations = any(
        r.get("invariant_violations", 0) > 0 for r in summary["results"]
    )
    sys.exit(1 if any_violations else 0)
