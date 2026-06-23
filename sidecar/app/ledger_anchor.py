"""Record verified ledger chain heads for external audit anchoring."""
from __future__ import annotations

import json
import logging
import urllib.request
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from .config import get_settings
from .ledger_seal import LedgerChainVerificationResult, verify_ledger_chain
from .metrics import get_counters

logger = logging.getLogger(__name__)


def schema_supports_ledger_anchors(session: Session) -> bool:
    dialect = session.bind.dialect.name
    if dialect == "postgresql":
        row = session.execute(
            text(
                """
                SELECT 1
                FROM information_schema.tables
                WHERE table_name = 'ledger_chain_anchors'
                """
            )
        ).first()
        return row is not None
    if dialect == "sqlite":
        row = session.execute(
            text(
                """
                SELECT 1 FROM sqlite_master
                WHERE type = 'table' AND name = 'ledger_chain_anchors'
                """
            )
        ).first()
        return row is not None
    return False


def anchor_verified_chain_head(
    session: Session,
    *,
    source: str = "api",
) -> dict[str, Any]:
    result = verify_ledger_chain(session)
    if not result.valid:
        get_counters().increment("ledger_chain_anchor_failed_total")
        raise ValueError(result.first_break.reason if result.first_break else "ledger chain invalid")

    if not result.head_hash:
        return {
            "anchored": False,
            "reason": "no sealed events",
            "sealed_count": result.sealed_count,
            "total_events": result.total_events,
        }

    if not schema_supports_ledger_anchors(session):
        _emit_external_anchor(result)
        return {
            "anchored": False,
            "reason": "anchor table unavailable",
            "head_hash": result.head_hash,
            "sealed_count": result.sealed_count,
        }

    inserted = None
    if session.bind.dialect.name == "sqlite":
        session.execute(
            text(
                """
                INSERT OR IGNORE INTO ledger_chain_anchors (
                    head_hash, sealed_count, total_events, source
                )
                VALUES (:head_hash, :sealed_count, :total_events, :source)
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
            text(
                """
                SELECT anchor_id FROM ledger_chain_anchors
                WHERE head_hash = :head_hash
                ORDER BY anchor_id DESC
                LIMIT 1
                """
            ),
            {"head_hash": result.head_hash},
        ).scalar_one_or_none()
    else:
        inserted = session.execute(
            text(
                """
                INSERT INTO ledger_chain_anchors (head_hash, sealed_count, total_events, source)
                VALUES (:head_hash, :sealed_count, :total_events, :source)
                ON CONFLICT DO NOTHING
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
        get_counters().increment("ledger_chain_anchor_recorded_total")
    _emit_external_anchor(result)

    return {
        "anchored": anchored,
        "anchor_id": int(inserted) if inserted is not None else None,
        "head_hash": result.head_hash,
        "sealed_count": result.sealed_count,
        "total_events": result.total_events,
        "source": source,
    }


def _emit_external_anchor(result: LedgerChainVerificationResult) -> None:
    settings = get_settings()
    if not settings.ledger_anchor_webhook_url or not result.head_hash:
        return
    payload = json.dumps(
        {
            "head_hash": result.head_hash,
            "sealed_count": result.sealed_count,
            "total_events": result.total_events,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        settings.ledger_anchor_webhook_url,
        data=payload,
        headers={"content-type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=5.0) as response:
            if response.status >= 400:
                logger.warning("ledger anchor webhook returned %s", response.status)
            else:
                get_counters().increment("ledger_chain_anchor_webhook_ok_total")
    except Exception as exc:
        logger.warning("ledger anchor webhook failed: %s", exc)
        get_counters().increment("ledger_chain_anchor_webhook_failed_total")
