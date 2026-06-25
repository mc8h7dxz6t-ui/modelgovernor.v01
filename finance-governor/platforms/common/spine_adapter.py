"""Spine adapter — platforms call Finance Governor spine or fall back to local mode."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from .crystal import Crystal, seal_crystal, should_strand_on_expiry, verify_commit_fingerprint


@dataclass
class CommitOutcome:
    operation_id: str
    crystal_id: str
    facets: dict[str, Any]
    outcome: str
    metadata: dict[str, Any] | None = None


class SpineAdapterError(Exception):
    pass


class SurpriseCommitBlocked(SpineAdapterError):
    """Commit attempted without valid crystal — Surprise Budget = 0."""


class HorizonStranded(SpineAdapterError):
    """Commit horizon expired — must STRAND, not guess."""


class LocalCrystalStore:
    """Standalone fallback when FG_SPINE_ENABLED=false."""

    def __init__(self) -> None:
        self._crystals: dict[str, Crystal] = {}

    def save(self, crystal: Crystal) -> None:
        self._crystals[crystal.crystal_id] = crystal

    def get(self, crystal_id: str) -> Crystal | None:
        return self._crystals.get(crystal_id)


class SpineAdapter:
    """
    Unified interface for Finance Governor spine integration.

    Spine mode: HTTP calls to fg-sidecar (:8091) crystallize / commit / adjudicate.
    Standalone mode: local crystal store with identical envelope semantics.
    """

    def __init__(
        self,
        platform: str,
        base_url: str | None = None,
        *,
        spine_enabled: bool | None = None,
        local_store: LocalCrystalStore | None = None,
    ) -> None:
        self.platform = platform
        self.base_url = base_url or os.environ.get("FG_SIDECAR_URL", "http://localhost:8091")
        enabled = spine_enabled if spine_enabled is not None else os.environ.get("FG_SPINE_ENABLED", "false").lower() == "true"
        self.spine_enabled = enabled
        self._local = local_store or LocalCrystalStore()

    def crystallize(
        self,
        operation_id: str,
        risk_tier: str,
        facets: dict[str, Any],
        *,
        parent_crystal_id: str | None = None,
        horizon_ms: int | None = None,
    ) -> Crystal:
        if self.spine_enabled:
            return self._http_crystallize(operation_id, risk_tier, facets, parent_crystal_id, horizon_ms)
        crystal = seal_crystal(
            platform=self.platform,
            operation_id=operation_id,
            risk_tier=risk_tier,
            facets=facets,
            parent_crystal_id=parent_crystal_id,
            horizon_ms=horizon_ms,
        )
        self._local.save(crystal)
        return crystal

    def commit(self, outcome: CommitOutcome) -> None:
        crystal = self._get_crystal(outcome.crystal_id)
        if crystal.terminal_state is not None:
            raise SurpriseCommitBlocked(f"crystal already terminal: {crystal.terminal_state}")
        if not verify_commit_fingerprint(crystal, outcome.facets):
            raise SurpriseCommitBlocked("commit fingerprint mismatch")
        from .crystal import is_horizon_expired

        if is_horizon_expired(crystal) and not outcome.metadata.get("late_authority"):
            if should_strand_on_expiry(crystal.risk_tier):
                raise HorizonStranded(f"horizon expired for {crystal.crystal_id}")
        if self.spine_enabled:
            self._http_commit(outcome)
        # standalone: terminal state recorded in local store via caller

    def strand(self, crystal_id: str, reason: str) -> None:
        if self.spine_enabled:
            self._http_strand(crystal_id, reason)

    def _get_crystal(self, crystal_id: str) -> Crystal:
        crystal = self._local.get(crystal_id)
        if crystal is not None:
            return crystal
        if self.spine_enabled:
            return self._http_get_crystal(crystal_id)
        raise SurpriseCommitBlocked(f"unknown crystal: {crystal_id}")

    # HTTP stubs — wired when spine sidecar is implemented
    def _http_crystallize(self, operation_id: str, risk_tier: str, facets: dict, parent: str | None, horizon_ms: int | None) -> Crystal:
        raise NotImplementedError("spine sidecar not yet deployed — use FG_SPINE_ENABLED=false for standalone")

    def _http_commit(self, outcome: CommitOutcome) -> None:
        raise NotImplementedError("spine sidecar not yet deployed")

    def _http_strand(self, crystal_id: str, reason: str) -> None:
        raise NotImplementedError("spine sidecar not yet deployed")

    def _http_get_crystal(self, crystal_id: str) -> Crystal:
        raise NotImplementedError("spine sidecar not yet deployed")
