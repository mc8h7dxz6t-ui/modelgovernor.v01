"""Governed crystallize → commit orchestration."""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

import httpx

from .config import Settings


def execute_governed_commit(
    settings: Settings,
    *,
    platform: str,
    operation_id: str | None,
    account_id: str,
    risk_tier: str,
    facets: dict[str, Any],
    policy_id: str | None,
    reserved_exposure: Decimal,
    committed_exposure: Decimal,
    outcome: str,
) -> dict[str, Any]:
    op_id = operation_id or f"gw-{uuid.uuid4().hex[:16]}"
    headers = {"x-internal-token": settings.cg_internal_token, "content-type": "application/json"}
    base = settings.cg_sidecar_url.rstrip("/")

    with httpx.Client(timeout=30.0) as client:
        crystallize = client.post(
            f"{base}/crystallize",
            headers=headers,
            json={
                "platform": platform,
                "operation_id": op_id,
                "account_id": account_id,
                "risk_tier": risk_tier,
                "facets": facets,
                "policy_id": policy_id,
                "reserved_exposure": str(reserved_exposure),
            },
        )
        crystallize.raise_for_status()
        crystal = crystallize.json()

        commit = client.post(
            f"{base}/commit",
            headers=headers,
            json={
                "crystal_id": crystal["crystal_id"],
                "facets": facets,
                "committed_exposure": str(committed_exposure),
                "outcome": outcome,
            },
        )
        commit.raise_for_status()
        result = commit.json()

    return {
        "operation_id": op_id,
        "crystal_id": crystal["crystal_id"],
        "crystallize_status": crystal["status"],
        "commit_status": result["status"],
    }
