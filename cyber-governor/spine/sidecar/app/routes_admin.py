import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from .auth import require_internal_auth, require_security_admin
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


class AdminAuditEntryResponse(BaseModel):
    audit_id: int
    actor_subject: str
    actor_method: str
    actor_roles: str | None
    action: str
    resource: str
    details: dict[str, Any]
    recorded_at: datetime | str


class AdminAuditLogResponse(BaseModel):
    entries: list[AdminAuditEntryResponse]
    total: int


def _parse_metadata(metadata: Any) -> dict[str, Any]:
    if metadata is None:
        return {}
    if isinstance(metadata, dict):
        return metadata
    if isinstance(metadata, str):
        try:
            parsed = json.loads(metadata)
        except json.JSONDecodeError:
            return {}
        if isinstance(parsed, dict):
            return parsed
    return {}


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
def diagnostic_clear(ctx=Depends(require_security_admin)) -> dict:
    from .admin_audit import record_admin_action
    from .diagnostic_mode import clear_diagnostic_mode

    with get_db_session() as session:
        record_admin_action(
            session,
            ctx=ctx,
            action="diagnostic_clear",
            resource="/internal/diagnostic/clear",
        )
        session.commit()
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
def post_security_anchor_head(ctx=Depends(require_security_admin)) -> SecurityAnchorResponse:
    from .admin_audit import record_admin_action

    with get_db_session() as session:
        try:
            record_admin_action(
                session,
                ctx=ctx,
                action="security_anchor_head",
                resource="/internal/security/anchor-head",
            )
            payload = anchor_verified_security_chain_head(session, source="admin_api")
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc
        session.commit()
    return SecurityAnchorResponse(**payload)


@router.get("/admin/audit/recent", response_model=AdminAuditLogResponse)
def get_recent_admin_audit(
    limit: int = Query(default=25, ge=1, le=200),
    _: None = Depends(require_internal_auth),
) -> AdminAuditLogResponse:
    from .admin_audit import schema_supports_admin_audit

    with get_db_session() as session:
        if not schema_supports_admin_audit(session):
            return AdminAuditLogResponse(entries=[], total=0)
        rows = session.execute(
            text(
                """
                SELECT audit_id, actor_subject, actor_method, actor_roles,
                       action, resource, details, recorded_at
                FROM admin_audit_log
                ORDER BY audit_id DESC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        ).mappings().all()
    entries = [
        AdminAuditEntryResponse(
            audit_id=row["audit_id"],
            actor_subject=row["actor_subject"],
            actor_method=row["actor_method"],
            actor_roles=row["actor_roles"],
            action=row["action"],
            resource=row["resource"],
            details=_parse_metadata(row["details"]),
            recorded_at=row["recorded_at"],
        )
        for row in rows
    ]
    return AdminAuditLogResponse(entries=entries, total=len(entries))
