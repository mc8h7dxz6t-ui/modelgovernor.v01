"""Regulatory export and examiner bundle APIs."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text

from .auth import AuthContext, require_internal_auth
from .claim_seal import head_hash, verify_claim_chain
from .db import get_db_session
from .guardrail_incidents import list_recent_incidents, schema_supports_guardrail_incidents

router = APIRouter(tags=["regulatory"], prefix="/internal")


@router.get("/regulatory/export")
def regulatory_export(
    limit: int = 500,
    _: AuthContext = Depends(require_internal_auth),
) -> dict:
    """Examiner bundle: chain verification, crystals, events, anchors, guardrails."""
    with get_db_session() as session:
        chain = verify_claim_chain(session)
        crystals = session.execute(
            text(
                """
                SELECT crystal_id, platform, operation_id, risk_tier, terminal_state, crystallized_at
                FROM governance_crystals
                ORDER BY crystallized_at DESC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        ).mappings().all()
        events = session.execute(
            text(
                """
                SELECT event_id, operation_id, crystal_id, account_id, event_type, reserve_delta, recorded_at
                FROM claim_events
                ORDER BY event_id DESC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        ).mappings().all()
        anchors = session.execute(
            text(
                """
                SELECT anchor_id, head_hash, sealed_count, total_events, source, recorded_at
                FROM claim_chain_anchors
                ORDER BY anchor_id DESC
                LIMIT 20
                """
            )
        ).mappings().all()
        incidents = list_recent_incidents(session, limit=limit) if schema_supports_guardrail_incidents(session) else []
        return {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "chain_verification": chain.to_dict(),
            "chain_head": head_hash(session),
            "crystals": [dict(c) for c in crystals],
            "claim_events": [dict(e) for e in events],
            "anchors": [dict(a) for a in anchors],
            "guardrail_incidents": incidents,
        }
