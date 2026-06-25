"""AlgoFreeze desk guard — MG+FG cross-wire before reserve."""
from __future__ import annotations

import logging

import httpx
from fastapi import HTTPException

from .config import Settings

logger = logging.getLogger(__name__)


def assert_desk_active_for_reserve(
    settings: Settings,
    *,
    request_id: str,
    runtime_sha: str | None = None,
) -> None:
    """Block ModelGovernor reserve when Finance Governor algo desk is FROZEN."""
    if not settings.algofreeze_enabled:
        return
    if not settings.algofreeze_url:
        return

    url = settings.algofreeze_url.rstrip("/")
    try:
        with httpx.Client(timeout=settings.algofreeze_timeout_seconds) as client:
            status = client.get(f"{url}/status")
            status.raise_for_status()
            body = status.json()
    except httpx.HTTPError as exc:
        logger.warning("algofreeze status check failed request_id=%s: %s", request_id, exc)
        if settings.algofreeze_fail_closed:
            raise HTTPException(
                status_code=503,
                detail=f"ALGOFREEZE_UNAVAILABLE: cannot verify desk state for request_id={request_id}",
            ) from exc
        return

    freeze_state = body.get("freeze_state", "ACTIVE")
    if freeze_state == "FROZEN":
        reason = body.get("reason") or "DESK_FROZEN"
        raise HTTPException(
            status_code=403,
            detail={
                "code": "ALGOFREEZE_BLOCKED",
                "message": f"reserve blocked: algo desk FROZEN ({reason})",
                "request_id": request_id,
                "freeze_state": freeze_state,
            },
        )

    if runtime_sha and body.get("approved_sha"):
        approved = body["approved_sha"]
        if runtime_sha != approved:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "DEPLOY_SHA_MISMATCH",
                    "message": "runtime SHA does not match approved deploy registry",
                    "request_id": request_id,
                    "runtime_sha": runtime_sha,
                    "approved_sha": approved,
                },
            )
