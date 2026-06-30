"""Integration mode labels — explicit sandbox vs production boundaries."""
from __future__ import annotations

import os
from enum import Enum


class IntegrationMode(str, Enum):
    SANDBOX = "sandbox"
    LIVE = "live"


def payment_rail_mode() -> IntegrationMode:
    raw = os.environ.get("PAYMENT_RAIL_MODE", "sandbox").lower()
    if raw in ("sandbox", "stub", "mock", "offline"):
        return IntegrationMode.SANDBOX
    return IntegrationMode.LIVE


def siem_export_mode() -> IntegrationMode:
    raw = os.environ.get("SIEM_EXPORT_MODE", "sandbox").lower()
    if raw in ("sandbox", "stub", "mock", "offline"):
        return IntegrationMode.SANDBOX
    return IntegrationMode.LIVE


def provider_mode() -> IntegrationMode:
    raw = os.environ.get("PROVIDER_MODE", "sandbox").lower()
    if raw in ("sandbox", "mock", "offline"):
        return IntegrationMode.SANDBOX
    return IntegrationMode.LIVE


def is_sandbox_mode(mode: IntegrationMode | str) -> bool:
    if isinstance(mode, IntegrationMode):
        return mode == IntegrationMode.SANDBOX
    return str(mode).lower() in ("sandbox", "stub", "mock", "offline")
