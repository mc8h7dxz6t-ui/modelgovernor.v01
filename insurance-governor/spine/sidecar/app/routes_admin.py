from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy import text

from .admin_audit import record_admin_action
from .auth import AuthContext, require_claims_admin, require_internal_auth
from .claim_anchor import anchor_verified_chain_head
from .claim_seal import head_hash, verify_claim_chain
from .db import get_db_session
from .diagnostic_mode import clear_diagnostic_mode, diagnostic_snapshot
from .guardrails import get_guardrails
from .metrics import get_counters
from .platform_guard import list_registered_platforms

router = APIRouter(tags=["admin"], prefix="/internal")


@router.get("/crystals/{crystal_id}")
def get_crystal(crystal_id: str, _: AuthContext = Depends(require_internal_auth)) -> dict:
    with get_db_session() as session:
        row = session.execute(
            text("SELECT * FROM governance_crystals WHERE crystal_id = :c"),
            {"c": crystal_id},
        ).mappings().first()
        if not row:
            return {"error": "not found"}
        return dict(row)


@router.get("/crystals/{crystal_id}/reconstruct")
def reconstruct_crystal(crystal_id: str, _: AuthContext = Depends(require_internal_auth)) -> dict:
    with get_db_session() as session:
        crystal = session.execute(
            text("SELECT * FROM governance_crystals WHERE crystal_id = :c"),
            {"c": crystal_id},
        ).mappings().first()
        if not crystal:
            return {"error": "not found"}
        events = session.execute(
            text("SELECT event_type, metadata, recorded_at FROM claim_events WHERE crystal_id = :c ORDER BY event_id"),
            {"c": crystal_id},
        ).mappings().all()
        escrow = session.execute(
            text("SELECT * FROM claim_escrow_ledger WHERE crystal_id = :c"),
            {"c": crystal_id},
        ).mappings().first()
        return {
            "crystal": dict(crystal),
            "escrow": dict(escrow) if escrow else None,
            "events": [dict(e) for e in events],
            "chain_head": head_hash(session),
        }


@router.get("/claims/verify-chain")
def verify_chain(_: AuthContext = Depends(require_internal_auth)) -> dict:
    with get_db_session() as session:
        result = verify_claim_chain(session)
        if not result.valid:
            get_counters().increment("claim_chain_verification_failed_total")
            raise HTTPException(status_code=422, detail=result.to_dict())
        return result.to_dict()


@router.post("/claims/anchor-head")
def anchor_head(ctx: AuthContext = Depends(require_claims_admin)) -> dict:
    with get_db_session() as session:
        try:
            result = anchor_verified_chain_head(session, source="api")
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        record_admin_action(session, ctx=ctx, action="ANCHOR_HEAD", resource="claim_chain", details=result)
        return result


@router.get("/diagnostic/status")
def diagnostic_status(_: AuthContext = Depends(require_internal_auth)) -> dict:
    snap = diagnostic_snapshot()
    snap["guardrails"] = get_guardrails().redis_status()
    return snap


@router.post("/diagnostic/clear")
def diagnostic_clear(ctx: AuthContext = Depends(require_claims_admin)) -> dict:
    clear_diagnostic_mode()
    with get_db_session() as session:
        record_admin_action(session, ctx=ctx, action="DIAGNOSTIC_CLEAR", resource="cluster")
    return {"cleared": True}


@router.get("/platforms")
def list_platforms(_: AuthContext = Depends(require_internal_auth)) -> list:
    with get_db_session() as session:
        return list_registered_platforms(session)


@router.get("/events/recent")
def recent_events(limit: int = 20, _: AuthContext = Depends(require_internal_auth)) -> list:
    with get_db_session() as session:
        rows = session.execute(
            text(
                "SELECT event_id, operation_id, event_type, recorded_at FROM claim_events ORDER BY event_id DESC LIMIT :l"
            ),
            {"l": limit},
        ).mappings().all()
        return [dict(r) for r in rows]


@router.get("/metrics")
def internal_metrics(_: AuthContext = Depends(require_internal_auth)) -> dict:
    return get_counters().snapshot()
