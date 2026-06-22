from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from pathlib import Path
import json
import sqlite3
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

sqlite3.register_adapter(Decimal, lambda value: str(value))

from sidecar.app.config import Settings
from sidecar.app.ledger import apply_settlement, reserve_operation
from sidecar.app.schemas import ReserveRequest, SettleRequest
from tests.integration.test_ledger_hardening import _bootstrap_schema, _seed_wallet_and_model

MONEY_QUANTUM = Decimal("0.000001")


def run_reserve_hotpath_harness(
    *,
    output_path: Path,
    operations: int = 120,
    workers: int = 12,
    reserved_amount: Decimal = Decimal("1.000000"),
    settled_amount: Decimal = Decimal("0.800000"),
) -> dict:
    engine = create_engine(
        f"sqlite:///{output_path.parent / 'reserve_hotpath.sqlite3'}",
        future=True,
        connect_args={"check_same_thread": False},
    )
    _bootstrap_schema(engine)
    _seed_wallet_and_model(engine, user_id="load-user", balance=Decimal("1000.000000"))

    settings = Settings(
        database_url=str(engine.url),
        redis_url="redis://example/0",
        sidecar_internal_tokens="test-token",
        default_trace_cap_amount=Decimal("1000000.000000"),
        drift_absolute_tolerance=Decimal("1000000.000000"),
        drift_ratio_tolerance=Decimal("1.000000"),
        db_pool_size=5,
        db_max_overflow=5,
        db_pool_timeout_seconds=5,
        db_pool_recycle_seconds=1800,
    )

    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    def run_operation(index: int) -> str:
        op_key = f"load-op-{index}"
        with factory() as session:
            reserve_operation(
                session,
                settings,
                ReserveRequest(
                    user_id="load-user",
                    trace_id=f"trace-{index}",
                    idempotency_key=op_key,
                    model="gpt-4o-mini",
                    estimated_cost=reserved_amount,
                ),
            )
        with factory() as session:
            apply_settlement(
                session,
                settings,
                SettleRequest(
                    idempotency_key=op_key,
                    outcome="SETTLED",
                    actual_cost=settled_amount,
                    provider_request_id=f"provider-{index}",
                ),
            )
        return "ok"

    with ThreadPoolExecutor(max_workers=workers) as pool:
        statuses = list(pool.map(run_operation, range(operations)))

    with Session(engine) as session:
        wallet_balance = Decimal(
            str(session.execute(text("SELECT balance FROM user_wallets WHERE user_id = 'load-user'")).scalar_one())
        ).quantize(MONEY_QUANTUM)
        settled_count = session.execute(
            text("SELECT COUNT(*) FROM escrow_ledger WHERE status = 'SETTLED'")
        ).scalar_one()
        reserve_events = session.execute(
            text("SELECT COUNT(*) FROM ledger_events WHERE event_type = 'RESERVE_CREATED'")
        ).scalar_one()
        settled_events = session.execute(
            text("SELECT COUNT(*) FROM ledger_events WHERE event_type = 'SETTLED_FINAL'")
        ).scalar_one()

    expected_balance = (Decimal("1000.000000") - (settled_amount * Decimal(operations))).quantize(
        MONEY_QUANTUM
    )
    report = {
        "harness": {
            "operations": operations,
            "workers": workers,
            "reserved_amount": str(reserved_amount),
            "settled_amount": str(settled_amount),
        },
        "results": {
            "operation_statuses_ok": statuses.count("ok"),
            "settled_rows": int(settled_count),
            "reserve_events": int(reserve_events),
            "settled_events": int(settled_events),
            "wallet_balance": str(wallet_balance),
            "expected_wallet_balance": str(expected_balance),
        },
        "invariants": {
            "all_operations_ok": statuses.count("ok") == operations,
            "all_rows_settled": int(settled_count) == operations,
            "event_counts_match": int(reserve_events) == operations and int(settled_events) == operations,
            "wallet_matches_settled_cost": wallet_balance == expected_balance,
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def test_reserve_hotpath_load_harness_outputs_invariant_report(tmp_path: Path) -> None:
    output_path = tmp_path / "reserve_hotpath_report.json"
    report = run_reserve_hotpath_harness(output_path=output_path, operations=80, workers=8)

    assert output_path.exists()
    assert report["invariants"]["all_operations_ok"] is True
    assert report["invariants"]["all_rows_settled"] is True
    assert report["invariants"]["event_counts_match"] is True
    assert report["invariants"]["wallet_matches_settled_cost"] is True
