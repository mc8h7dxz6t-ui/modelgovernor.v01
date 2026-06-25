"""Crystal Commit Protocol — shared spine primitive."""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any


@dataclass(frozen=True)
class Crystal:
    crystal_id: str
    platform: str
    operation_id: str
    risk_tier: str
    facets: dict[str, Any]
    request_fingerprint: str
    crystal_hash: str
    prev_crystal_hash: str | None
    parent_crystal_id: str | None
    horizon_expires_at: datetime
    terminal_state: str | None = None
    crystallized_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# Risk-tier default horizons (ms) — overridden by instrument_policy_registry
HORIZON_MS: dict[str, int] = {
    "critical": 5_000,
    "high": 300_000,
    "standard": 3_600_000,
}


def canonical_fingerprint(platform: str, operation_id: str, facets: dict[str, Any]) -> str:
    payload = json.dumps(
        {"platform": platform, "operation_id": operation_id, "facets": facets},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def seal_crystal(
    *,
    platform: str,
    operation_id: str,
    risk_tier: str,
    facets: dict[str, Any],
    prev_crystal_hash: str | None = None,
    parent_crystal_id: str | None = None,
    horizon_ms: int | None = None,
) -> Crystal:
    """Create a Governance Crystal — immutable context snapshot before irreversible action."""
    crystal_id = f"crys_{uuid.uuid4().hex}"
    fingerprint = canonical_fingerprint(platform, operation_id, facets)
    ms = horizon_ms if horizon_ms is not None else HORIZON_MS.get(risk_tier, HORIZON_MS["standard"])
    now = datetime.now(timezone.utc)
    body = json.dumps(
        {
            "crystal_id": crystal_id,
            "platform": platform,
            "operation_id": operation_id,
            "risk_tier": risk_tier,
            "facets": facets,
            "fingerprint": fingerprint,
            "prev": prev_crystal_hash,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    crystal_hash = hashlib.sha256(body.encode()).hexdigest()
    return Crystal(
        crystal_id=crystal_id,
        platform=platform,
        operation_id=operation_id,
        risk_tier=risk_tier,
        facets=facets,
        request_fingerprint=fingerprint,
        crystal_hash=crystal_hash,
        prev_crystal_hash=prev_crystal_hash,
        parent_crystal_id=parent_crystal_id,
        horizon_expires_at=now + timedelta(milliseconds=ms),
    )


def verify_commit_fingerprint(crystal: Crystal, commit_facets: dict[str, Any]) -> bool:
    """Commit must match crystal facets — Surprise Budget = 0."""
    return canonical_fingerprint(crystal.platform, crystal.operation_id, commit_facets) == crystal.request_fingerprint


def is_horizon_expired(crystal: Crystal, now: datetime | None = None) -> bool:
    ts = now or datetime.now(timezone.utc)
    return ts >= crystal.horizon_expires_at


def should_strand_on_expiry(risk_tier: str) -> bool:
    """CCP rule: critical and high never guess on horizon expiry."""
    return risk_tier in ("critical", "high")
