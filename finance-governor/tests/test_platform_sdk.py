"""Platform SDK — governed operation and app bootstrap."""
from __future__ import annotations

import pytest

from platforms.common.platform_sdk import (
    CommitOutcome,
    PlatformConfig,
    create_platform_app,
    governed_operation,
    spine_adapter_for,
)
from platforms.common.spine_adapter import LocalCrystalStore, SpineAdapter


def test_create_platform_app_registers_counters():
    config = PlatformConfig(
        name="demo_platform",
        display_name="Demo",
        invariant_counters=("custom_event_total",),
    )
    app = create_platform_app(config)
    assert app.state.platform_config.name == "demo_platform"


def test_governed_operation_local_crystallize_and_commit():
    store = LocalCrystalStore()
    adapter = SpineAdapter("wire_match", spine_enabled=False, local_store=store)
    facets = {"amount": "100.00"}
    with governed_operation(adapter, "op-local-1", facets, risk_tier="high") as ctx:
        assert ctx.crystal_id
        adapter.commit(
            CommitOutcome(
                operation_id=ctx.operation_id,
                crystal_id=ctx.crystal_id,
                facets=facets,
                outcome="approved",
            )
        )


def test_governed_operation_rejects_bad_facets():
    adapter = spine_adapter_for(PlatformConfig(name="wire_match", display_name="Wire"))
    with pytest.raises(Exception):
        with governed_operation(adapter, "op-bad", {"currency": "USD"}):
            pass


def test_spine_adapter_strand_local_unknown():
    adapter = SpineAdapter("wire_match", spine_enabled=False)
    with pytest.raises(Exception):
        adapter.strand("missing-crystal")
