"""Property-based ledger invariant tests (Hypothesis state-space exploration)."""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from tempfile import mkdtemp
from uuid import uuid4

import pytest

pytest.importorskip("hypothesis")
from hypothesis import given, settings
from hypothesis import strategies as st
from sqlalchemy import text
from sqlalchemy.orm import Session

from sidecar.app.config import Settings
from sidecar.app.ledger import reserve_operation
from sidecar.app.schemas import ReserveRequest
from tests.integration.test_ledger_hardening import _bootstrap_schema, _create_test_engine, _seed_wallet_and_model

MONEY = st.decimals(min_value=Decimal("0.01"), max_value=Decimal("5"), places=2)


@settings(max_examples=25, deadline=None)
@given(cost=MONEY, replays=st.integers(min_value=1, max_value=5))
def test_reserve_idempotent_replay_always_returns_same_result(cost: Decimal, replays: int) -> None:
    db_path = Path(mkdtemp()) / f"prop-{uuid4().hex}.sqlite3"
    engine = _create_test_engine(db_path)
    _bootstrap_schema(engine)
    _seed_wallet_and_model(engine, user_id="prop-user", balance=Decimal("1000"))
    cfg = Settings(
        database_url=str(engine.url),
        redis_url="redis://example/0",
        sidecar_internal_tokens="test-token",
        default_trace_cap_amount=Decimal("10000"),
        drift_absolute_tolerance=Decimal("100"),
        drift_ratio_tolerance=Decimal("1"),
        db_pool_size=2,
        db_max_overflow=2,
        db_pool_timeout_seconds=5,
        db_pool_recycle_seconds=1800,
    )
    request = ReserveRequest(
        user_id="prop-user",
        trace_id="prop-trace",
        idempotency_key="prop-op",
        model="gpt-4o-mini",
        estimated_cost=cost,
    )

    first = None
    for _ in range(replays):
        with Session(engine) as session:
            result = reserve_operation(session, cfg, request)
            if first is None:
                first = result
            else:
                assert result.idempotency_key == first.idempotency_key
                assert result.status == first.status
                assert result.actual_amount == first.actual_amount

    with Session(engine) as session:
        rows = session.execute(
            text("SELECT COUNT(*) FROM escrow_ledger WHERE idempotency_key = 'prop-op'")
        ).scalar_one()
    assert int(rows) == 1
