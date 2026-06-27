"""Record verified decision chain heads for external audit anchoring."""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from .decision_seal import verify_decision_chain
from .metrics import get_counters

logger = logging.getLogger(__name__)


def schema_supports_decision_anchors(session: Session) -> bool:
    dialect = session.bind.dialect.name
    if dialect == "postgresql":
        row = session.execute(
            text("SELECT 1 FROM information_schema.tables WHERE table_name = 'decision_chain_anchors'")
        ).first()
        return row is not None
    if dialect == "sqlite":
        row = session.execute(
            text("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'decision_chain_anchors'")
        ).first()
        return row is not None
    return False


def anchor_verified_decision_head(session: Session, *, source: str = "api") -> dict[str, Any]:
    result = verify_decision_chain(session)
    if not result.valid:
        get_counters().increment("ledger_chain_verification_failed_total")
        raise ValueError(result.first_break.reason if result.first_break else "decision chain invalid")

    if not result.head_hash:
        return {
            "anchored": False,
            "reason": "no sealed events",
            "sealed_count": result.sealed_count,
            "total_events": result.total_events,
        }

    from .decision_anchor_s3 import anchor_head_to_s3

    s3_result = anchor_head_to_s3(
        head_hash=result.head_hash,
        sealed_count=result.sealed_count,
        total_events=result.total_events,
        source=source,
    )

    if not schema_supports_decision_anchors(session):
        return {
            "anchored": False,
            "reason": "anchor table unavailable",
            "head_hash": result.head_hash,
            "sealed_count": result.sealed_count,
            "s3_anchored": s3_result.get("s3_anchored", False),
            "s3_key": s3_result.get("s3_key"),
        }

    if session.bind.dialect.name == "sqlite":
        session.execute(
            text(
                """
                INSERT OR IGNORE INTO decision_chain_anchors (
                    head_hash, sealed_count, total_events, source
                ) VALUES (:head_hash, :sealed_count, :total_events, :source)
                """
            ),
            {
                "head_hash": result.head_hash,
                "sealed_count": result.sealed_count,
                "total_events": result.total_events,
                "source": source,
            },
        )
        inserted = session.execute(
            text("SELECT anchor_id FROM decision_chain_anchors WHERE head_hash = :h ORDER BY anchor_id DESC LIMIT 1"),
            {"h": result.head_hash},
        ).scalar_one_or_none()
    else:
        inserted = session.execute(
            text(
                """
                INSERT INTO decision_chain_anchors (head_hash, sealed_count, total_events, source)
                VALUES (:head_hash, :sealed_count, :total_events, :source)
                ON CONFLICT (head_hash) DO NOTHING
                RETURNING anchor_id
                """
            ),
            {
                "head_hash": result.head_hash,
                "sealed_count": result.sealed_count,
                "total_events": result.total_events,
                "source": source,
            },
        ).scalar_one_or_none()

    anchored = inserted is not None
    if anchored:
        get_counters().increment("decision_chain_anchor_recorded_total")

    return {
        "anchored": anchored,
        "anchor_id": int(inserted) if inserted is not None else None,
        "head_hash": result.head_hash,
        "sealed_count": result.sealed_count,
        "total_events": result.total_events,
        "source": source,
        "s3_anchored": s3_result.get("s3_anchored", False),
        "s3_key": s3_result.get("s3_key"),
    }
