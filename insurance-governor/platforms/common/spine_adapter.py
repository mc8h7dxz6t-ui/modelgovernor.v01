"""Spine adapter — platforms use Insurance Governor spine or local fallback."""
from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from .crystal import (
    Crystal,
    is_horizon_expired,
    seal_crystal,
    should_strand_on_expiry,
    verify_commit_fingerprint,
)


@dataclass
class CommitOutcome:
    operation_id: str
    crystal_id: str
    facets: dict[str, Any]
    outcome: str
    committed_reserve: str = "0"
    metadata: dict[str, Any] | None = None


class SpineAdapterError(Exception):
    pass


class SurpriseCommitBlocked(SpineAdapterError):
    pass


class HorizonStranded(SpineAdapterError):
    pass


class LocalCrystalStore:
    def __init__(self) -> None:
        self._crystals: dict[str, Crystal] = {}

    def save(self, crystal: Crystal) -> None:
        self._crystals[crystal.crystal_id] = crystal

    def get(self, crystal_id: str) -> Crystal | None:
        return self._crystals.get(crystal_id)


class LocalPlatformEventLog:
    """Append-only platform events when spine is disabled (standalone mode)."""

    def __init__(self, db_path: str | None = None) -> None:
        path = db_path or os.environ.get("IG_PLATFORM_EVENTS_DB", ":memory:")
        self._path = path
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS platform_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                operation_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                recorded_at TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def append(self, platform: str, operation_id: str, event_type: str, payload: dict[str, Any]) -> None:
        self._conn.execute(
            "INSERT INTO platform_events (platform, operation_id, event_type, payload, recorded_at) VALUES (?, ?, ?, ?, ?)",
            (
                platform,
                operation_id,
                event_type,
                json.dumps(payload, sort_keys=True),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        self._conn.commit()


class SpineAdapter:
    def __init__(
        self,
        platform: str,
        base_url: str | None = None,
        *,
        spine_enabled: bool | None = None,
        internal_token: str | None = None,
        local_store: LocalCrystalStore | None = None,
        event_log: LocalPlatformEventLog | None = None,
    ) -> None:
        self.platform = platform
        self.base_url = (base_url or os.environ.get("IG_SIDECAR_URL", "http://localhost:8101")).rstrip("/")
        if spine_enabled is not None:
            enabled = spine_enabled
        else:
            enabled = os.environ.get("IG_SPINE_ENABLED", "false").lower() == "true"
        self.spine_enabled = enabled
        self._token = internal_token or os.environ.get("IG_INTERNAL_TOKEN", "dev-ig-spine-token-change-me")
        self._local = local_store or LocalCrystalStore()
        self._events = event_log or LocalPlatformEventLog()

    def _headers(self) -> dict[str, str]:
        return {"x-internal-token": self._token, "content-type": "application/json"}

    def crystallize(
        self,
        operation_id: str,
        risk_tier: str,
        facets: dict[str, Any],
        *,
        account_id: str = "carrier-default",
        policy_id: str | None = None,
        reserved_reserve: str = "0",
        parent_crystal_id: str | None = None,
    ) -> Crystal:
        if self.spine_enabled:
            return self._http_crystallize(
                operation_id, risk_tier, facets, account_id, policy_id, reserved_reserve, parent_crystal_id
            )
        crystal = seal_crystal(
            platform=self.platform,
            operation_id=operation_id,
            risk_tier=risk_tier,
            facets=facets,
            parent_crystal_id=parent_crystal_id,
        )
        self._local.save(crystal)
        self._events.append(self.platform, operation_id, "CRYSTAL_CREATED", {"crystal_id": crystal.crystal_id, "facets": facets})
        return crystal

    def commit(self, outcome: CommitOutcome) -> None:
        if self.spine_enabled:
            self._http_commit(outcome)
            return
        crystal = self._local.get(outcome.crystal_id)
        if crystal is None:
            raise SurpriseCommitBlocked(f"unknown crystal: {outcome.crystal_id}")
        if not verify_commit_fingerprint(crystal, outcome.facets):
            raise SurpriseCommitBlocked("fingerprint mismatch")
        if is_horizon_expired(crystal) and not (outcome.metadata or {}).get("late_authority"):
            if should_strand_on_expiry(crystal.risk_tier):
                raise HorizonStranded("horizon expired")
        self._events.append(
            self.platform,
            outcome.operation_id,
            "COMMITTED",
            {"crystal_id": outcome.crystal_id, "outcome": outcome.outcome, "facets": outcome.facets},
        )

    def _http_crystallize(
        self,
        operation_id: str,
        risk_tier: str,
        facets: dict,
        account_id: str,
        policy_id: str | None,
        reserved_reserve: str,
        parent_crystal_id: str | None,
    ) -> Crystal:
        with httpx.Client(timeout=30.0) as client:
            r = client.post(
                f"{self.base_url}/crystallize",
                headers=self._headers(),
                json={
                    "platform": self.platform,
                    "operation_id": operation_id,
                    "account_id": account_id,
                    "risk_tier": risk_tier,
                    "facets": facets,
                    "policy_id": policy_id,
                    "reserved_reserve": reserved_reserve,
                    "parent_crystal_id": parent_crystal_id,
                },
            )
            r.raise_for_status()
            data = r.json()
        local = seal_crystal(
            platform=self.platform,
            operation_id=operation_id,
            risk_tier=risk_tier,
            facets=facets,
            parent_crystal_id=parent_crystal_id,
        )
        horizon = data["horizon_expires_at"]
        if isinstance(horizon, str):
            horizon = datetime.fromisoformat(horizon.replace("Z", "+00:00"))
        return Crystal(
            crystal_id=data["crystal_id"],
            platform=self.platform,
            operation_id=operation_id,
            risk_tier=risk_tier,
            facets=facets,
            request_fingerprint=local.request_fingerprint,
            crystal_hash=local.crystal_hash,
            prev_crystal_hash=local.prev_crystal_hash,
            parent_crystal_id=parent_crystal_id,
            horizon_expires_at=horizon,
        )

    def _http_commit(self, outcome: CommitOutcome) -> None:
        with httpx.Client(timeout=30.0) as client:
            r = client.post(
                f"{self.base_url}/commit",
                headers=self._headers(),
                json={
                    "crystal_id": outcome.crystal_id,
                    "facets": outcome.facets,
                    "committed_reserve": outcome.committed_reserve,
                    "outcome": outcome.outcome,
                    "late_authority": bool((outcome.metadata or {}).get("late_authority")),
                },
            )
            if r.status_code == 409:
                detail = r.json().get("detail", "")
                if "horizon" in str(detail).lower():
                    raise HorizonStranded(detail)
                raise SurpriseCommitBlocked(detail)
            r.raise_for_status()
