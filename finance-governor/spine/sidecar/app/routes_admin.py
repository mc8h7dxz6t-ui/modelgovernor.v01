from fastapi import APIRouter, Depends, HTTPException

from .admin_audit import record_admin_action, schema_supports_admin_audit
from .auth import AuthContext, require_financial_admin, require_internal_auth
from .db import get_db_session, get_read_db_session
from .decision_anchor import anchor_verified_decision_head
from .decision_seal import head_hash, verify_decision_chain
from .diagnostic_mode import clear_diagnostic_mode, diagnostic_snapshot
from .metrics import get_counters
from sqlalchemy import text

router = APIRouter(tags=["admin"], prefix="/internal")


@router.get("/decisions/verify-chain")
def verify_chain(_: AuthContext = Depends(require_internal_auth)) -> dict:
    with get_read_db_session() as read_session, get_db_session() as write_session:
        result = verify_decision_chain(write_session, incremental=True, read_session=read_session)
        if not result.valid:
            get_counters().increment("ledger_chain_verification_failed_total")
            raise HTTPException(status_code=422, detail=result.to_dict())
        return result.to_dict()


@router.post("/decisions/anchor-head")
def anchor_decision_head(_: AuthContext = Depends(require_financial_admin)) -> dict:
    with get_db_session() as session:
        try:
            result = anchor_verified_decision_head(session, source="api")
            session.commit()
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return result


@router.get("/crystals/{crystal_id}")
def get_crystal(crystal_id: str, _: AuthContext = Depends(require_internal_auth)) -> dict:
    with get_db_session() as session:
        row = session.execute(
            text("SELECT * FROM governance_crystals WHERE crystal_id = :c"),
            {"c": crystal_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="crystal not found")
        return dict(row)


@router.get("/crystals/{crystal_id}/reconstruct")
def reconstruct_crystal(crystal_id: str, _: AuthContext = Depends(require_internal_auth)) -> dict:
    with get_db_session() as session:
        crystal = session.execute(
            text("SELECT * FROM governance_crystals WHERE crystal_id = :c"),
            {"c": crystal_id},
        ).mappings().first()
        if not crystal:
            raise HTTPException(status_code=404, detail="crystal not found")
        events = session.execute(
            text(
                "SELECT event_type, metadata, recorded_at FROM decision_events WHERE crystal_id = :c ORDER BY event_id"
            ),
            {"c": crystal_id},
        ).mappings().all()
        escrow = session.execute(
            text("SELECT * FROM commit_escrow_ledger WHERE crystal_id = :c"),
            {"c": crystal_id},
        ).mappings().first()
        return {
            "crystal": dict(crystal),
            "escrow": dict(escrow) if escrow else None,
            "events": [dict(e) for e in events],
            "chain_head": head_hash(session),
        }


@router.get("/diagnostic/status")
def diagnostic_status(_: AuthContext = Depends(require_internal_auth)) -> dict:
    return diagnostic_snapshot()


@router.post("/diagnostic/clear")
def diagnostic_clear(auth: AuthContext = Depends(require_financial_admin)) -> dict:
    with get_db_session() as session:
        record_admin_action(
            session,
            actor_subject=auth.subject,
            actor_method=auth.method,
            action="diagnostic_clear",
            target="cluster",
        )
        session.commit()
    clear_diagnostic_mode()
    return {"cleared": True}


@router.get("/admin/audit/recent")
def recent_admin_audit(limit: int = 20, _: AuthContext = Depends(require_internal_auth)) -> list:
    with get_db_session() as session:
        if not schema_supports_admin_audit(session):
            return []
        rows = session.execute(
            text(
                """
                SELECT audit_id, actor_subject, action, target, recorded_at
                FROM admin_audit_log ORDER BY audit_id DESC LIMIT :l
                """
            ),
            {"l": limit},
        ).mappings().all()
        return [dict(r) for r in rows]


@router.get("/events/recent")
def recent_events(limit: int = 20, _: AuthContext = Depends(require_internal_auth)) -> list:
    with get_db_session() as session:
        rows = session.execute(
            text("SELECT event_id, operation_id, event_type, recorded_at FROM decision_events ORDER BY event_id DESC LIMIT :l"),
            {"l": limit},
        ).mappings().all()
        return [dict(r) for r in rows]


@router.get("/metrics")
def internal_metrics(_: AuthContext = Depends(require_internal_auth)) -> dict:
    return get_counters().snapshot()
