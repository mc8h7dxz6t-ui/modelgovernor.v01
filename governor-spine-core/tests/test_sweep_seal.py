"""K3 — reconciler sweep hash-seal conformance and ModelGovernor runtime proof."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from spine_core.sweep_seal import SWEEP_APPEND_REGISTRY, SWEEP_EVENT_TYPES, sweep_conformance_failures

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def test_k3_all_four_governors_registered():
    assert len(SWEEP_APPEND_REGISTRY) == 4
    assert len(SWEEP_EVENT_TYPES) == 4


def test_k3_sweep_conformance_no_failures():
    failures = sweep_conformance_failures(REPO_ROOT)
    assert failures == [], "K3 sweep seal gaps:\n" + "\n".join(failures)


def test_mg_sweeper_seals_ledger_events(tmp_path) -> None:
    from reconciler.app.sweeper import sweep_expired_reservations
    from sidecar.app.ledger_seal import verify_ledger_chain
    from tests.integration.test_ledger_hardening import (
        _bootstrap_schema,
        _create_test_engine,
        _seed_wallet_and_model,
    )

    engine = _create_test_engine(tmp_path / "mg-sweep-seal.sqlite3")
    _bootstrap_schema(engine)
    _seed_wallet_and_model(engine, user_id="user-1")

    with Session(engine) as session:
        session.execute(
            text(
                """
                INSERT INTO escrow_ledger (
                    idempotency_key, user_id, trace_id, model, request_fingerprint,
                    reserved_amount, status, expires_at
                ) VALUES (
                    'sweep-op', 'user-1', 'trace-sweep', 'gpt-4o-mini', 'fp',
                    10.0, 'RESERVED', :expires_at
                )
                """
            ),
            {"expires_at": datetime.now(timezone.utc) - timedelta(minutes=5)},
        )
        session.commit()

    with Session(engine) as session:
        assert sweep_expired_reservations(session, batch_size=10) == 1

    with Session(engine) as session:
        result = verify_ledger_chain(session)
        assert result.valid is True
        assert result.unsealed_count == 0
        assert result.sealed_count >= 1
        event = session.execute(
            text(
                "SELECT event_type, row_hash FROM ledger_events WHERE idempotency_key = 'sweep-op'"
            )
        ).mappings().one()
        assert event["event_type"] == "EXPIRED_SWEEP"
        assert event["row_hash"] is not None
