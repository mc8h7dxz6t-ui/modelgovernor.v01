from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from .auth import require_internal_auth
from .db import get_db_session
from .security_seal import head_hash, verify_security_chain
from .security_anchor import anchor_verified_security_chain_head
from .diagnostic_mode import diagnostic_snapshot
from .metrics import get_counters
from sqlalchemy import text

router = APIRouter(tags=["admin"], prefix="/internal")


class SecurityChainVerificationResponse(BaseModel):
    valid: bool
    sealed_count: int
    unsealed_count: int
    total_events: int
    head_hash: str | None = None


class SecurityAnchorResponse(BaseModel):
    anchored: bool
    anchor_id: int | None = None
    head_hash: str | None = None
    sealed_count: int | None = None
    total_events: int | None = None
    first_event_id: int | None = None
    last_event_id: int | None = None
    source: str | None = None
    s3_anchored: bool = False
    s3_key: str | None = None
    reason: str | None = None


@router.get("/crystals/{crystal_id}")
def get_crystal(crystal_id: str, _: None = Depends(require_internal_auth)) -> dict:
    with get_db_session() as session:
        row = session.execute(
            text("SELECT * FROM threat_crystals WHERE crystal_id = :c"),
            {"c": crystal_id},
        ).mappings().first()
        if not row:
            return {"error": "not found"}
        return dict(row)


@router.get("/crystals/{crystal_id}/reconstruct")
def reconstruct_crystal(crystal_id: str, _: None = Depends(require_internal_auth)) -> dict:
    with get_db_session() as session:
        crystal = session.execute(
            text("SELECT * FROM threat_crystals WHERE crystal_id = :c"),
            {"c": crystal_id},
        ).mappings().first()
        if not crystal:
            return {"error": "not found"}
        events = session.execute(
            text(
                "SELECT event_type, metadata, recorded_at FROM security_events WHERE crystal_id = :c ORDER BY event_id"
            ),
            {"c": crystal_id},
        ).mappings().all()
        escrow = session.execute(
            text("SELECT * FROM action_escrow_ledger WHERE crystal_id = :c"),
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
            text("SELECT event_id, operation_id, event_type, recorded_at FROM security_events ORDER BY event_id DESC LIMIT :l"),
            {"l": limit},
        ).mappings().all()
        return [dict(r) for r in rows]


@router.get("/metrics")
def internal_metrics(_: None = Depends(require_internal_auth)) -> dict:
    return get_counters().snapshot()


@router.get("/security/verify-chain", response_model=SecurityChainVerificationResponse)
def get_security_verify_chain(_: None = Depends(require_internal_auth)) -> SecurityChainVerificationResponse:
    with get_db_session() as session:
        result = verify_security_chain(session)
    if not result.valid:
        get_counters().increment("security_chain_verification_failed_total")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=result.to_dict(),
        )
    get_counters().increment("security_chain_verification_ok_total")
    return SecurityChainVerificationResponse(**result.to_dict())


@router.post("/security/anchor-head", response_model=SecurityAnchorResponse)
def post_security_anchor_head(_: None = Depends(require_internal_auth)) -> SecurityAnchorResponse:
    with get_db_session() as session:
        try:
            payload = anchor_verified_security_chain_head(session, source="admin_api")
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc
        session.commit()
    return SecurityAnchorResponse(**payload)
