from fastapi import APIRouter, Depends, HTTPException

from .auth import require_internal_auth
from .db import get_db_session
from .decision_seal import head_hash, verify_decision_chain
from .diagnostic_mode import diagnostic_snapshot
from .metrics import get_counters
from sqlalchemy import text

router = APIRouter(tags=["admin"], prefix="/internal")


@router.get("/decisions/verify-chain")
def verify_chain(_: None = Depends(require_internal_auth)) -> dict:
    with get_db_session() as session:
        result = verify_decision_chain(session)
        if not result.valid:
            get_counters().increment("ledger_chain_verification_failed_total")
        return result.to_dict()


@router.get("/crystals/{crystal_id}")
def get_crystal(crystal_id: str, _: None = Depends(require_internal_auth)) -> dict:
    with get_db_session() as session:
        row = session.execute(
            text("SELECT * FROM governance_crystals WHERE crystal_id = :c"),
            {"c": crystal_id},
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="crystal not found")
        return dict(row)


@router.get("/crystals/{crystal_id}/reconstruct")
def reconstruct_crystal(crystal_id: str, _: None = Depends(require_internal_auth)) -> dict:
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
def diagnostic_status(_: None = Depends(require_internal_auth)) -> dict:
    return diagnostic_snapshot()


@router.post("/diagnostic/clear")
def diagnostic_clear(_: None = Depends(require_internal_auth)) -> dict:
    from .diagnostic_mode import clear_diagnostic_mode

    clear_diagnostic_mode()
    return {"cleared": True}


@router.get("/events/recent")
def recent_events(limit: int = 20, _: None = Depends(require_internal_auth)) -> list:
    with get_db_session() as session:
        rows = session.execute(
            text("SELECT event_id, operation_id, event_type, recorded_at FROM decision_events ORDER BY event_id DESC LIMIT :l"),
            {"l": limit},
        ).mappings().all()
        return [dict(r) for r in rows]


@router.get("/metrics")
def internal_metrics(_: None = Depends(require_internal_auth)) -> dict:
    return get_counters().snapshot()
