"""Property-based security hash chain tests (Hypothesis state-space exploration)."""
from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path
from tempfile import mkdtemp
from uuid import uuid4

import pytest
from hypothesis import given, settings as hyp_settings
from hypothesis import strategies as st
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
SIDECAR = ROOT / "spine" / "sidecar"
sys.path.insert(0, str(SIDECAR))

from tests.helpers import create_sqlite_engine, session_factory

pytest.importorskip("hypothesis")

EVENT_TYPES = st.sampled_from(
    ["CRYSTALLIZED", "COMMITTED", "STRANDED_HOLD", "MESH_BLOCK", "WITNESS_RECEIVED"]
)
EXPOSURE = st.decimals(min_value=Decimal("0"), max_value=Decimal("1000"), places=2)
META_KEYS = st.text(min_size=1, max_size=12, alphabet=st.characters(whitelist_categories=("L", "N")))


@hyp_settings(max_examples=30, deadline=None)
@given(
    event_count=st.integers(min_value=1, max_value=12),
    exposures=st.lists(EXPOSURE, min_size=1, max_size=12),
    types=st.lists(EVENT_TYPES, min_size=1, max_size=12),
)
def test_append_events_always_yields_valid_chain(
    event_count: int,
    exposures: list[Decimal],
    types: list[str],
) -> None:
    from app.event_ledger import append_security_event
    from app.security_seal import verify_security_chain

    db_path = Path(mkdtemp()) / f"prop-chain-{uuid4().hex}.sqlite3"
    engine = create_sqlite_engine(db_path)
    Session = session_factory(engine)

    with Session() as s:
        for i in range(event_count):
            append_security_event(
                s,
                operation_id=f"prop-op-{i}",
                crystal_id=f"tcrys-{i}",
                account_id="tenant-default",
                event_type=types[i % len(types)],
                exposure_delta=exposures[i % len(exposures)],
                metadata={"seq": i, "probe": "hypothesis"},
            )
            s.commit()
        result = verify_security_chain(s)
        assert result.valid is True
        assert result.sealed_count == event_count
        assert result.unsealed_count == 0
        assert result.head_hash is not None


@hyp_settings(max_examples=20, deadline=None)
@given(exposure=EXPOSURE, event_type=EVENT_TYPES)
def test_tampered_row_hash_breaks_chain(exposure: Decimal, event_type: str) -> None:
    from app.event_ledger import append_security_event
    from app.security_seal import verify_security_chain

    db_path = Path(mkdtemp()) / f"prop-tamper-{uuid4().hex}.sqlite3"
    engine = create_sqlite_engine(db_path)
    Session = session_factory(engine)

    with Session() as s:
        for i in range(3):
            append_security_event(
                s,
                operation_id=f"tamper-{i}",
                crystal_id=f"tcrys-{i}",
                account_id="tenant-default",
                event_type=event_type,
                exposure_delta=exposure,
            )
            s.commit()
        s.execute(
            text("UPDATE security_events SET row_hash = :bad WHERE event_id = 2"),
            {"bad": "f" * 64},
        )
        s.commit()
        result = verify_security_chain(s)
        assert result.valid is False
        assert result.first_break is not None
        assert "row_hash mismatch" in result.first_break.reason


@hyp_settings(max_examples=20, deadline=None)
@given(exposure=EXPOSURE)
def test_tampered_prev_hash_breaks_chain(exposure: Decimal) -> None:
    from app.event_ledger import append_security_event
    from app.security_seal import verify_security_chain

    db_path = Path(mkdtemp()) / f"prop-prev-{uuid4().hex}.sqlite3"
    engine = create_sqlite_engine(db_path)
    Session = session_factory(engine)

    with Session() as s:
        for i in range(3):
            append_security_event(
                s,
                operation_id=f"prev-{i}",
                crystal_id=f"tcrys-{i}",
                account_id="tenant-default",
                event_type="COMMITTED",
                exposure_delta=exposure,
            )
            s.commit()
        s.execute(
            text("UPDATE security_events SET prev_hash = :bad WHERE event_id = 2"),
            {"bad": "a" * 64},
        )
        s.commit()
        result = verify_security_chain(s)
        assert result.valid is False
        assert result.first_break is not None
        assert "prev_hash mismatch" in result.first_break.reason


@hyp_settings(max_examples=25, deadline=None)
@given(
    operation_id=st.text(min_size=4, max_size=24, alphabet=st.characters(whitelist_categories=("L", "N"))),
    exposure=EXPOSURE,
    meta_key=META_KEYS,
)
def test_compute_row_hash_is_deterministic(
    operation_id: str,
    exposure: Decimal,
    meta_key: str,
) -> None:
    from app.currency import quantize_money
    from app.security_seal import compute_row_hash

    metadata = {meta_key: "value"}
    exposure_str = str(quantize_money(exposure))
    recorded_at = "2026-01-01T00:00:00+00:00"
    kwargs = dict(
        event_id=1,
        operation_id=operation_id,
        crystal_id="tcrys-1",
        account_id="tenant-default",
        event_type="COMMITTED",
        exposure_delta=exposure_str,
        metadata=metadata,
        prev_hash="0" * 64,
        recorded_at=recorded_at,
    )
    assert compute_row_hash(**kwargs) == compute_row_hash(**kwargs)


@hyp_settings(max_examples=20, deadline=None)
@given(replays=st.integers(min_value=2, max_value=6))
def test_crystallize_idempotent_replay_preserves_single_crystal(replays: int) -> None:
    from app.commit_ledger import crystallize_operation

    db_path = Path(mkdtemp()) / f"prop-replay-{uuid4().hex}.sqlite3"
    engine = create_sqlite_engine(db_path)
    from tests.helpers import cg_settings

    settings = cg_settings(str(engine.url))
    Session = session_factory(engine)
    facets = {"session_state": "AUTHORIZED", "user_id": "prop@corp.example"}

    first_id = None
    for _ in range(replays):
        with Session() as s:
            cr = crystallize_operation(
                s,
                settings,
                platform="identity_gate",
                operation_id="prop-replay-op",
                account_id="tenant-default",
                risk_tier="critical",
                facets=facets,
            )
            if first_id is None:
                first_id = cr.crystal_id
            else:
                assert cr.crystal_id == first_id
                assert cr.status == "REPLAY"

    with Session() as s:
        count = s.execute(
            text("SELECT COUNT(*) FROM threat_crystals WHERE operation_id = 'prop-replay-op'")
        ).scalar_one()
    assert int(count) == 1
