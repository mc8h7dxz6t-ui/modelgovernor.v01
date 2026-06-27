from fastapi import APIRouter, Depends, HTTPException

from .auth import require_internal_auth
from .db import get_db_session
from .platform_registry import get_platform, list_platforms

router = APIRouter(tags=["platforms"], prefix="/internal/platforms")


@router.get("")
def platforms_index(_=Depends(require_internal_auth)) -> list[dict]:
    with get_db_session() as session:
        return [
            {
                "platform_name": p.platform_name,
                "display_name": p.display_name,
                "enabled": p.enabled,
                "base_url": p.base_url,
                "default_policy_id": p.default_policy_id,
                "default_risk_tier": p.default_risk_tier,
                "facet_schema": p.facet_schema,
                "invariant_counters": p.invariant_counters,
            }
            for p in list_platforms(session)
        ]


@router.get("/{platform_name}")
def platform_detail(platform_name: str, _=Depends(require_internal_auth)) -> dict:
    with get_db_session() as session:
        record = get_platform(session, platform_name)
        if record is None:
            raise HTTPException(status_code=404, detail="platform not found")
        return {
            "platform_name": record.platform_name,
            "display_name": record.display_name,
            "enabled": record.enabled,
            "base_url": record.base_url,
            "default_policy_id": record.default_policy_id,
            "default_risk_tier": record.default_risk_tier,
            "facet_schema": record.facet_schema,
            "invariant_counters": record.invariant_counters,
        }
