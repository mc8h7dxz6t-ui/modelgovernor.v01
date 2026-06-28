"""Tests for FNOL write-back adapters."""
from __future__ import annotations

import os

from platforms.common.integrations.fnol_writeback import (
    sync_fnol_decision,
    writeback_enabled,
)


def test_writeback_defaults_to_dry_run(monkeypatch):
    monkeypatch.delenv("FNOL_WRITEBACK_MODE", raising=False)
    assert writeback_enabled() is False
    result = sync_fnol_decision(
        vendor="guidewire",
        claim_id="GW-1",
        decision="APPROVED",
        facets={"net_payable": "100.00"},
    )
    assert result.dry_run is True
    assert result.status == "dry_run_recorded"
    assert result.external_ref == "dry-GW-1"


def test_ice_writeback_dry_run(monkeypatch):
    monkeypatch.setenv("FNOL_WRITEBACK_MODE", "dry_run")
    result = sync_fnol_decision(
        vendor="ice",
        claim_id="ICE-UK-1",
        decision="HELD",
        facets={"gate_score": 0.42},
    )
    assert result.vendor == "ice"
    assert result.status == "dry_run_recorded"


def test_unsupported_writeback_vendor(monkeypatch):
    monkeypatch.setenv("FNOL_WRITEBACK_MODE", "live")
    result = sync_fnol_decision(
        vendor="majesco",
        claim_id="MJ-1",
        decision="APPROVED",
        facets={},
    )
    assert result.status == "unsupported_vendor"
