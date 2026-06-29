"""Ledger chain verification — fail-closed when seal schema is absent."""
from __future__ import annotations

from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from sidecar.app.ledger_seal import verify_ledger_chain
from tests.integration.test_ledger_hardening import (
    _bootstrap_schema,
    _create_test_engine,
    _seed_wallet_and_model,
)


def test_verify_chain_fails_without_seal_columns(tmp_path: Path) -> None:
    engine = _create_test_engine(tmp_path / "mg-seal-failclosed.sqlite3")
    _bootstrap_schema(engine)
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE ledger_events ADD COLUMN prev_hash CHAR(64)"))
        connection.execute(text("ALTER TABLE ledger_events ADD COLUMN row_hash CHAR(64)"))
    _seed_wallet_and_model(engine, user_id="user-1")

    with Session(engine) as session:
        session.execute(
            text(
                """
                INSERT INTO ledger_events (idempotency_key, user_id, event_type, amount_delta, metadata)
                VALUES ('op-1', 'user-1', 'RESERVED', 1.0, '{}')
                """
            )
        )
        session.commit()

    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE ledger_events DROP COLUMN row_hash"))

    with Session(engine) as session:
        result = verify_ledger_chain(session)
        assert result.valid is False
        assert result.first_break is not None
        assert result.first_break.reason == "seal_schema_unavailable"


def test_verify_chain_empty_without_seal_columns(tmp_path: Path) -> None:
    """Empty ledger without seal columns still fails closed — cannot attest integrity."""
    engine = _create_test_engine(tmp_path / "mg-seal-empty.sqlite3")
    _bootstrap_schema(engine)
    _seed_wallet_and_model(engine, user_id="user-1")

    with Session(engine) as session:
        result = verify_ledger_chain(session)
        assert result.valid is False
        assert result.first_break is not None
        assert result.first_break.reason == "seal_schema_unavailable"
