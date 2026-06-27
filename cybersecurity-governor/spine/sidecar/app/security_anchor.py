"""Record verified claim chain heads for external audit anchoring."""
from __future__ import annotations

import json
import logging
import urllib.request
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from .security_seal import SecurityChainVerificationResult, verify_security_chain
from .config import get_settings
from .metrics import get_counters

logger = logging.getLogger(__name__)


def schema_supports_security_anchors(session: Session) -> bool:
    dialect = session.bind.dialect.name
    if dialect == "postgresql":
        row = session.execute(
            text("SELECT 1 FROM information_schema.tables WHERE table_name = 'security_chain_anchors'")
        ).first()
        return row is not None
    if dialect == "sqlite":
        row = session.execute(
            text("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'security_chain_anchors'")
        ).first()
        return row is not None
    return False


def anchor_verified_chain_head(session: Session, *, source: str = "api") -> dict[str, Any]:
    result = verify_security_chain(session)
    if not result.valid:
        get_counters().increment("security_chain_anchor_failed_total")
        raise ValueError(result.first_break.reason if result.first_break else "claim chain invalid")

    if not result.head_hash:
        return {
            "anchored": False,
            "reason": "no sealed events",
            "sealed_count": result.sealed_count,
            "total_events": result.total_events,
        }

    if not schema_supports_security_anchors(session):
        external = _emit_external_anchor(result, source=source)
        s3_result = external.get("s3") or {}
        return {
            "anchored": False,
            "reason": "anchor table unavailable",
            "head_hash": result.head_hash,
            "sealed_count": result.sealed_count,
            "s3_anchored": s3_result.get("s3_anchored", False),
            "s3_key": s3_result.get("s3_key"),
        }

    inserted = None
    if session.bind.dialect.name == "sqlite":
        before = session.execute(text("SELECT COUNT(*) FROM security_chain_anchors")).scalar_one()
        session.execute(
            text(
                """
                INSERT OR IGNORE INTO security_chain_anchors (head_hash, sealed_count, total_events, source)
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
        after = session.execute(text("SELECT COUNT(*) FROM security_chain_anchors")).scalar_one()
        anchored = int(after) > int(before)
        if anchored:
            inserted = session.execute(
                text(
                    """
                    SELECT anchor_id FROM security_chain_anchors
                    WHERE head_hash = :head_hash ORDER BY anchor_id DESC LIMIT 1
                    """
                ),
                {"head_hash": result.head_hash},
            ).scalar_one_or_none()
    else:
        inserted = session.execute(
            text(
                """
                INSERT INTO security_chain_anchors (head_hash, sealed_count, total_events, source)
                VALUES (:head_hash, :sealed_count, :total_events, :source)
                ON CONFLICT DO NOTHING RETURNING anchor_id
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
        get_counters().increment("security_chain_anchor_recorded_total")
    external = _emit_external_anchor(result, source=source)
    s3_result = external.get("s3", {})
    session.commit()
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


def _emit_external_anchor(result: SecurityChainVerificationResult, *, source: str) -> dict[str, Any]:
    settings = get_settings()
    payload: dict[str, Any] = {"webhook": None, "s3": None}
    if not result.head_hash:
        return payload

    from .security_anchor_s3 import anchor_head_to_s3

    payload["s3"] = anchor_head_to_s3(
        head_hash=result.head_hash,
        sealed_count=result.sealed_count,
        total_events=result.total_events,
        source=source,
    )

    if not settings.security_anchor_webhook_url:
        return payload
    webhook_body = json.dumps(
        {
            "head_hash": result.head_hash,
            "sealed_count": result.sealed_count,
            "total_events": result.total_events,
            "source": source,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        settings.security_anchor_webhook_url,
        data=webhook_body,
        headers={"content-type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=5.0) as response:
            if response.status >= 400:
                logger.warning("claim anchor webhook returned %s", response.status)
            else:
                get_counters().increment("security_chain_anchor_webhook_ok_total")
    except Exception as exc:
        logger.warning("claim anchor webhook failed: %s", exc)
        get_counters().increment("security_chain_anchor_webhook_failed_total")
    return payload
