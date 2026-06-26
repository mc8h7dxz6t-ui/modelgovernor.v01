"""Regulatory export, attribution summary, and guardrail incident APIs."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text

from .auth import AuthContext, require_internal_auth
from .db import get_db_session
from .decision_seal import head_hash, verify_decision_chain
from .guardrail_incidents import list_recent_incidents, schema_supports_guardrail_incidents

router = APIRouter(tags=["regulatory"], prefix="/internal")


@router.get("/regulatory/export")
def regulatory_export(
    limit: int = 500,
    _: AuthContext = Depends(require_internal_auth),
) -> dict:
    """Examiner bundle: chain verification, recent crystals, events, anchors, guardrails."""
    with get_db_session() as session:
        chain = verify_decision_chain(session)
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
                SELECT event_id, operation_id, crystal_id, account_id, event_type, exposure_delta, recorded_at
                FROM decision_events
                ORDER BY event_id DESC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        ).mappings().all()
        anchors = session.execute(
            text(
                """
                SELECT anchor_id, head_hash, sealed_count, total_events, source, anchored_at
                FROM decision_chain_anchors
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
            "decision_events": [dict(e) for e in events],
            "anchors": [dict(a) for a in anchors],
            "guardrail_incidents": incidents,
        }


@router.get("/attribution/summary")
def attribution_summary(
    _: AuthContext = Depends(require_internal_auth),
) -> dict:
    """Aggregate committed exposure by desk_id and platform from crystal facets."""
    with get_db_session() as session:
        rows = session.execute(
            text(
                """
                SELECT c.platform, c.facets, e.committed_exposure
                FROM governance_crystals c
                JOIN commit_escrow_ledger e ON e.crystal_id = c.crystal_id
                WHERE c.terminal_state = 'COMMITTED'
                """
            )
        ).mappings().all()
        by_desk: dict[str, dict] = {}
        by_platform: dict[str, dict] = {}
        for row in rows:
            facets = row["facets"]
            if isinstance(facets, str):
                facets = json.loads(facets)
            desk = facets.get("desk_id") or facets.get("account_id") or "unknown"
            platform = row["platform"]
            committed = float(row["committed_exposure"] or 0)
            desk_bucket = by_desk.setdefault(desk, {"desk_id": desk, "committed_total": 0.0, "commit_count": 0})
            desk_bucket["committed_total"] += committed
            desk_bucket["commit_count"] += 1
            plat_bucket = by_platform.setdefault(platform, {"platform": platform, "committed_total": 0.0, "commit_count": 0})
            plat_bucket["committed_total"] += committed
            plat_bucket["commit_count"] += 1
        return {
            "by_desk": sorted(by_desk.values(), key=lambda x: x["committed_total"], reverse=True),
            "by_platform": sorted(by_platform.values(), key=lambda x: x["committed_total"], reverse=True),
        }


@router.get("/guardrail/incidents")
def guardrail_incidents(
    limit: int = 50,
    _: AuthContext = Depends(require_internal_auth),
) -> list:
    with get_db_session() as session:
        return list_recent_incidents(session, limit=limit)
