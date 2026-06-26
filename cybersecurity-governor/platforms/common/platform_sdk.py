"""Plug-and-play platform SDK — any platform integrates via manifest + SpineAdapter."""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from .spine_adapter import CommitOutcome, HorizonStranded, SpineAdapter, SurpriseCommitBlocked
from .platform_metrics import get_platform_counters, register_platform_counters

logger = logging.getLogger(__name__)

PLATFORMS_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = PLATFORMS_ROOT / "registry.yaml"


@dataclass(frozen=True)
class PlatformManifest:
    name: str
    display_name: str
    default_policy_id: str
    default_risk_tier: str = "high"
    port: int = 8123
    docker_image: str = ""
    required_facet_keys: tuple[str, ...] = ()
    commit_decisions: frozenset[str] = frozenset({"APPROVED"})
    invariant_counters: tuple[str, ...] = ()

    @classmethod
    def from_mapping(cls, name: str, data: dict[str, Any]) -> PlatformManifest:
        return cls(
            name=data.get("name", name),
            display_name=str(data.get("display_name", name)),
            default_policy_id=str(data["default_policy_id"]),
            default_risk_tier=str(data.get("default_risk_tier", "high")),
            port=int(data.get("port", 8123)),
            docker_image=str(data.get("docker_image", "")),
            required_facet_keys=tuple(data.get("required_facet_keys", ())),
            commit_decisions=frozenset(data.get("commit_decisions", ("APPROVED",))),
            invariant_counters=tuple(data.get("invariant_counters", ())),
        )

    @classmethod
    def load(cls, platform: str) -> PlatformManifest:
        per_platform = PLATFORMS_ROOT / platform / "manifest.yaml"
        if per_platform.is_file():
            data = yaml.safe_load(per_platform.read_text()) or {}
            return cls.from_mapping(platform, data)
        catalog = load_registry()
        if platform not in catalog:
            raise KeyError(f"unknown platform: {platform}")
        return catalog[platform]

    def validate_facets(self, facets: dict[str, Any]) -> list[str]:
        missing = [key for key in self.required_facet_keys if key not in facets]
        return missing


@lru_cache(maxsize=1)
def load_registry() -> dict[str, PlatformManifest]:
    if not REGISTRY_PATH.is_file():
        return {}
    raw = yaml.safe_load(REGISTRY_PATH.read_text()) or {}
    entries = raw.get("platforms", {})
    return {name: PlatformManifest.from_mapping(name, cfg) for name, cfg in entries.items()}


class GovernedPlatform:
    """Standard CCP govern path for any registered platform."""

    def __init__(
        self,
        platform: str | PlatformManifest,
        *,
        spine_enabled: bool | None = None,
    ) -> None:
        self.manifest = platform if isinstance(platform, PlatformManifest) else PlatformManifest.load(platform)
        if self.manifest.invariant_counters:
            register_platform_counters(self.manifest.name, self.manifest.invariant_counters)
        if spine_enabled is None:
            spine_enabled = os.environ.get("CG_SPINE_ENABLED", "false").lower() == "true"
        self._adapter = SpineAdapter(platform=self.manifest.name, spine_enabled=spine_enabled)

    def validate_facets(self, facets: dict[str, Any]) -> None:
        missing = self.manifest.validate_facets(facets)
        if missing:
            raise ValueError(f"missing required facets: {', '.join(missing)}")

    def govern_operation(
        self,
        operation_id: str,
        facets: dict[str, Any],
        *,
        decision: str,
        reserve_amount: str,
        account_id: str = "tenant-default",
        policy_id: str | None = None,
        outcome: str | None = None,
    ) -> str | None:
        self.validate_facets(facets)
        policy = policy_id or self.manifest.default_policy_id
        should_commit = decision in self.manifest.commit_decisions
        reserve = reserve_amount if should_commit else "0"
        try:
            crystal = self._adapter.crystallize(
                operation_id=operation_id,
                risk_tier=self.manifest.default_risk_tier,
                facets=facets,
                account_id=account_id,
                policy_id=policy,
                reserved_budget=reserve,
            )
            if should_commit:
                self._adapter.commit(
                    CommitOutcome(
                        operation_id=operation_id,
                        crystal_id=crystal.crystal_id,
                        facets=facets,
                        outcome=outcome or decision.lower(),
                        committed_budget=reserve,
                    )
                )
            return crystal.crystal_id
        except (SurpriseCommitBlocked, HorizonStranded) as exc:
            logger.warning("govern blocked platform=%s op=%s: %s", self.manifest.name, operation_id, exc)
            return None
        except Exception as exc:
            logger.warning("govern failed platform=%s op=%s: %s", self.manifest.name, operation_id, exc)
            return None


def spine_health_payload(platform: str) -> dict[str, Any]:
    enabled = os.environ.get("CG_SPINE_ENABLED", "false").lower() == "true"
    return {"status": "ok", "platform": platform, "spine_enabled": enabled}


def increment_invariant(platform: str, counter: str, delta: int = 1) -> None:
    get_platform_counters(platform).increment(counter, delta)
