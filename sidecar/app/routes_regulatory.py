"""Regulatory export and examiner bundle APIs."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text

from .auth import AuthContext, require_internal_auth
from .db import get_db_session, get_read_db_session
from .diagnostic_mode import diagnostic_snapshot
from .ledger_seal import head_hash, verify_ledger_chain

router = APIRouter(tags=["regulatory"], prefix="/internal")


@router.get("/regulatory/export")
def regulatory_export(
    limit: int = 500,
    _: AuthContext = Depends(require_internal_auth),
) -> dict:
    """Examiner bundle: chain verification, escrow ops, events, anchors, diagnostic state."""
    with get_read_db_session() as read_session, get_db_session() as write_session:
        chain = verify_ledger_chain(write_session, incremental=True, read_session=read_session)
        crystals = read_session.execute(
            text(
                """
                SELECT idempotency_key, user_id, status, reserved_amount, actual_amount, created_at
                FROM escrow_ledger
                ORDER BY created_at DESC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        ).mappings().all()
        events = read_session.execute(
            text(
                """
                SELECT event_id, idempotency_key, user_id, event_type, amount_delta, recorded_at
                FROM ledger_events
                ORDER BY event_id DESC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        ).mappings().all()
        anchors = []
        if read_session.bind.dialect.name == "postgresql":
            row = read_session.execute(
                text(
                    "SELECT 1 FROM information_schema.tables WHERE table_name = 'ledger_chain_anchors'"
                )
            ).first()
            if row:
                anchors = read_session.execute(
                    text(
                        """
                        SELECT anchor_id, head_hash, sealed_count, total_events, source, recorded_at
                        FROM ledger_chain_anchors
                        ORDER BY anchor_id DESC
                        LIMIT 20
                        """
                    )
                ).mappings().all()
        else:
            row = read_session.execute(
                text("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'ledger_chain_anchors'")
            ).first()
            if row:
                anchors = read_session.execute(
                    text(
                        """
                        SELECT anchor_id, head_hash, sealed_count, total_events, source, recorded_at
                        FROM ledger_chain_anchors
                        ORDER BY anchor_id DESC
                        LIMIT 20
                        """
                    )
                ).mappings().all()
        incidents = []
        if read_session.bind.dialect.name == "postgresql":
            has_incidents = read_session.execute(
                text("SELECT 1 FROM information_schema.tables WHERE table_name = 'guardrail_incidents'")
            ).first()
        else:
            has_incidents = read_session.execute(
                text("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'guardrail_incidents'")
            ).first()
        if has_incidents:
            incidents = read_session.execute(
                text(
                    """
                    SELECT incident_id, incident_type, user_id, metadata, recorded_at
                    FROM guardrail_incidents
                    ORDER BY incident_id DESC
                    LIMIT :limit
                    """
                ),
                {"limit": limit},
            ).mappings().all()
        return {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "chain_verification": chain.to_dict(),
            "chain_head": head_hash(read_session),
            "escrow_operations": [dict(c) for c in crystals],
            "ledger_events": [dict(e) for e in events],
            "anchors": [dict(a) for a in anchors],
            "guardrail_incidents": [dict(i) for i in incidents],
            "diagnostic": diagnostic_snapshot(),
        }
