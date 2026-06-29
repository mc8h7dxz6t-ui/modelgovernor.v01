"""Shared spine integration helpers for fleet platforms."""
from __future__ import annotations

import logging
from typing import Any

from .platform_sdk import PlatformConfig, spine_enabled
from .spine_adapter import CommitOutcome, SpineAdapter

logger = logging.getLogger(__name__)


def adapter_for(config: PlatformConfig) -> SpineAdapter:
    return SpineAdapter(platform=config.name, spine_enabled=spine_enabled())


def crystallize(
    config: PlatformConfig,
    operation_id: str,
    facets: dict[str, Any],
    *,
    risk_tier: str | None = None,
    policy_id: str | None = None,
    reserved_exposure: str = "0",
    account_id: str = "desk-default",
) -> str | None:
    if not spine_enabled():
        return None
    try:
        adapter = adapter_for(config)
        crystal = adapter.crystallize(
            operation_id=operation_id,
            risk_tier=risk_tier or config.default_risk_tier,
            facets=facets,
            account_id=account_id,
            policy_id=policy_id or config.default_policy_id,
            reserved_exposure=reserved_exposure,
        )
        return crystal.crystal_id
    except Exception as exc:
        logger.warning("spine crystallize failed platform=%s operation=%s: %s", config.name, operation_id, exc)
        return None


def crystallize_and_commit(
    config: PlatformConfig,
    operation_id: str,
    facets: dict[str, Any],
    *,
    risk_tier: str | None = None,
    policy_id: str | None = None,
    reserved_exposure: str = "0",
    committed_exposure: str = "0",
    outcome: str = "committed",
    account_id: str = "desk-default",
    metadata: dict[str, Any] | None = None,
) -> str | None:
    if not spine_enabled():
        return None
    try:
        adapter = adapter_for(config)
        crystal = adapter.crystallize(
            operation_id=operation_id,
            risk_tier=risk_tier or config.default_risk_tier,
            facets=facets,
            account_id=account_id,
            policy_id=policy_id or config.default_policy_id,
            reserved_exposure=reserved_exposure,
        )
        adapter.commit(
            CommitOutcome(
                operation_id=operation_id,
                crystal_id=crystal.crystal_id,
                facets=facets,
                outcome=outcome,
                committed_exposure=committed_exposure,
                metadata=metadata,
            )
        )
        return crystal.crystal_id
    except Exception as exc:
        logger.warning("spine crystallize/commit failed platform=%s operation=%s: %s", config.name, operation_id, exc)
        return None
