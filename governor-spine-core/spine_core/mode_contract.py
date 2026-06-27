"""Runtime mode contract — maps Active/Mock semantics to existing governor env vars.

This module does NOT replace per-governor circuit breakers, guardrails, or diagnostic mode.
It documents the authoritative mapping for due-diligence and salvage verification.
"""

from __future__ import annotations

import os
from enum import Enum

from spine_core.config import GovernorDomain


class RuntimeExecutionMode(str, Enum):
    ACTIVE = "live"
    MOCK = "mock"


class SpineAttachmentMode(str, Enum):
    """Whether a platform wedge calls the spine or uses local SQLite fallback."""

    SPINE_ENABLED = "spine"
    STANDALONE = "standalone"


def resolve_provider_mode() -> RuntimeExecutionMode:
    raw = os.getenv("PROVIDER_MODE", "mock").strip().lower()
    if raw in {"live", "active"}:
        return RuntimeExecutionMode.ACTIVE
    return RuntimeExecutionMode.MOCK


def resolve_spine_attachment(domain: GovernorDomain) -> SpineAttachmentMode:
    keys = {
        GovernorDomain.MODEL: None,
        GovernorDomain.FINANCE: "FG_SPINE_ENABLED",
        GovernorDomain.INSURANCE: "IG_SPINE_ENABLED",
        GovernorDomain.CYBER: "CG_SPINE_ENABLED",
    }
    env_key = keys[domain]
    if env_key is None:
        return SpineAttachmentMode.SPINE_ENABLED
    raw = os.getenv(env_key, "true").strip().lower()
    if raw in {"false", "0", "no"}:
        return SpineAttachmentMode.STANDALONE
    return SpineAttachmentMode.SPINE_ENABLED


def failover_env_contract() -> dict[str, str]:
    """Document existing degradation knobs (implemented in each governor's sidecar)."""
    return {
        "PROVIDER_MODE": "ModelGovernor gateway — live vs mock LLM providers",
        "FG_SPINE_ENABLED": "Finance platforms — spine vs local adapter",
        "IG_SPINE_ENABLED": "Insurance platforms — spine vs local adapter",
        "CG_SPINE_ENABLED": "Cyber platforms — spine vs local adapter",
        "DIAGNOSTIC_MODE": "Sidecar write halt (reads continue)",
        "GUARDRAILS_ENABLED": "Redis rate/depth limits with local fallback",
        "CIRCUIT_BREAKER_ENABLED": "Redis dependency circuit breaker",
    }
