"""Incremental hash-chain verification checkpoints — O(delta) verify at scale."""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class VerifyCheckpoint:
    last_verified_event_id: int
    verified_head_hash: str
    sealed_count: int
    total_events: int


def schema_supports_checkpoints(session: Session, checkpoint_table: str) -> bool:
    dialect = session.bind.dialect.name
    if dialect == "postgresql":
        row = session.execute(
            text(
                """
                SELECT 1 FROM information_schema.tables
                WHERE table_name = :table_name
                """
            ),
            {"table_name": checkpoint_table},
        ).first()
        return row is not None
    if dialect == "sqlite":
        row = session.execute(
            text("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = :table_name"),
            {"table_name": checkpoint_table},
        ).first()
        return row is not None
    return False


def load_checkpoint(session: Session, checkpoint_table: str) -> VerifyCheckpoint | None:
    if not schema_supports_checkpoints(session, checkpoint_table):
        return None
    row = session.execute(
        text(
            f"""
            SELECT last_verified_event_id, verified_head_hash, sealed_count, total_events
            FROM {checkpoint_table}
            ORDER BY checkpoint_id DESC
            LIMIT 1
            """
        )
    ).mappings().first()
    if not row:
        return None
    return VerifyCheckpoint(
        last_verified_event_id=int(row["last_verified_event_id"]),
        verified_head_hash=str(row["verified_head_hash"]),
        sealed_count=int(row["sealed_count"]),
        total_events=int(row["total_events"]),
    )


def save_checkpoint(session: Session, checkpoint_table: str, checkpoint: VerifyCheckpoint) -> None:
    if not schema_supports_checkpoints(session, checkpoint_table):
        return
    dialect = session.bind.dialect.name
    params = {
        "last_verified_event_id": checkpoint.last_verified_event_id,
        "verified_head_hash": checkpoint.verified_head_hash,
        "sealed_count": checkpoint.sealed_count,
        "total_events": checkpoint.total_events,
    }
    if dialect == "sqlite":
        session.execute(text(f"DELETE FROM {checkpoint_table}"))
        session.execute(
            text(
                f"""
                INSERT INTO {checkpoint_table} (
                    last_verified_event_id, verified_head_hash, sealed_count, total_events
                ) VALUES (
                    :last_verified_event_id, :verified_head_hash, :sealed_count, :total_events
                )
                """
            ),
            params,
        )
    else:
        session.execute(
            text(
                f"""
                INSERT INTO {checkpoint_table} (
                    last_verified_event_id, verified_head_hash, sealed_count, total_events
                ) VALUES (
                    :last_verified_event_id, :verified_head_hash, :sealed_count, :total_events
                )
                ON CONFLICT (singleton_key) DO UPDATE SET
                    last_verified_event_id = EXCLUDED.last_verified_event_id,
                    verified_head_hash = EXCLUDED.verified_head_hash,
                    sealed_count = EXCLUDED.sealed_count,
                    total_events = EXCLUDED.total_events,
                    verified_at = CURRENT_TIMESTAMP
                """
            ),
            params,
        )


def count_events(session: Session, events_table: str) -> int:
    return int(session.execute(text(f"SELECT COUNT(*) FROM {events_table}")).scalar_one())
