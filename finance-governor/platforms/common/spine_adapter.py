"""Spine adapter — platforms call Finance Governor spine or fall back to local mode."""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
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
    committed_exposure: str = "0"
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


class SpineAdapter:
    def __init__(
        self,
        platform: str,
        base_url: str | None = None,
        *,
        spine_enabled: bool | None = None,
        internal_token: str | None = None,
        local_store: LocalCrystalStore | None = None,
    ) -> None:
        self.platform = platform
        self.base_url = (base_url or os.environ.get("FG_SIDECAR_URL", "http://localhost:8091")).rstrip("/")
        enabled = spine_enabled if spine_enabled is not None else os.environ.get("FG_SPINE_ENABLED", "false").lower() == "true"
        self.spine_enabled = enabled
        self._token = internal_token or os.environ.get("FG_INTERNAL_TOKEN", "dev-fg-spine-token-change-me")
        self._local = local_store or LocalCrystalStore()

    def _headers(self) -> dict[str, str]:
        return {"x-internal-token": self._token, "content-type": "application/json"}

    def crystallize(
        self,
        operation_id: str,
        risk_tier: str,
        facets: dict[str, Any],
        *,
        account_id: str = "desk-default",
        policy_id: str | None = None,
        reserved_exposure: str = "0",
        parent_crystal_id: str | None = None,
    ) -> Crystal:
        if self.spine_enabled:
            return self._http_crystallize(
                operation_id, risk_tier, facets, account_id, policy_id, reserved_exposure, parent_crystal_id
            )
        crystal = seal_crystal(
            platform=self.platform,
            operation_id=operation_id,
            risk_tier=risk_tier,
            facets=facets,
            parent_crystal_id=parent_crystal_id,
        )
        self._local.save(crystal)
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

    def strand(self, crystal_id: str, reason: str = "manual_strand") -> None:
        if self.spine_enabled:
            self._http_strand(crystal_id, reason)
            return
        crystal = self._local.get(crystal_id)
        if crystal is None:
            raise SurpriseCommitBlocked(f"unknown crystal: {crystal_id}")

    def _request_with_retry(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                with httpx.Client(timeout=30.0) as client:
                    response = getattr(client, method)(url, **kwargs)
                if response.status_code >= 500 and attempt < 2:
                    time.sleep(0.1 * (2**attempt))
                    continue
                return response
            except httpx.HTTPError as exc:
                last_exc = exc
                if attempt < 2:
                    time.sleep(0.1 * (2**attempt))
        if last_exc:
            raise SpineAdapterError(str(last_exc)) from last_exc
        raise SpineAdapterError("request failed")

    def _http_crystallize(
        self,
        operation_id: str,
        risk_tier: str,
        facets: dict,
        account_id: str,
        policy_id: str | None,
        reserved_exposure: str,
        parent_crystal_id: str | None,
    ) -> Crystal:
        from datetime import datetime

        r = self._request_with_retry(
            "post",
            f"{self.base_url}/crystallize",
            headers=self._headers(),
            json={
                "platform": self.platform,
                "operation_id": operation_id,
                "account_id": account_id,
                "risk_tier": risk_tier,
                "facets": facets,
                "policy_id": policy_id,
                "reserved_exposure": reserved_exposure,
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
        r = self._request_with_retry(
            "post",
            f"{self.base_url}/commit",
            headers=self._headers(),
            json={
                "crystal_id": outcome.crystal_id,
                "facets": outcome.facets,
                "committed_exposure": outcome.committed_exposure,
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

    def _http_strand(self, crystal_id: str, reason: str) -> None:
        r = self._request_with_retry(
            "post",
            f"{self.base_url}/adjudicate",
            headers=self._headers(),
            json={"crystal_id": crystal_id, "action": "strand", "reason": reason},
        )
        if r.status_code == 409:
            raise SurpriseCommitBlocked(r.json().get("detail", "strand blocked"))
        r.raise_for_status()
