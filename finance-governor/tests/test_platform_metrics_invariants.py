"""Gold-standard platform invariant counter tests."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from platforms.common.platform_metrics import get_platform_counters


@pytest.fixture(autouse=True)
def _fresh_counters():
    import platforms.common.platform_metrics as pm

    for plat in list(pm._counters_by_platform):
        pm._counters_by_platform[plat] = pm.PlatformCounters()
    yield


def test_algofreeze_frozen_egress_counter():
    c = get_platform_counters("algofreeze")
    c.increment("frozen_egress_attempt_total")
    assert c.snapshot()["frozen_egress_attempt_total"] == 1


def test_wirematch_held_counter():
    c = get_platform_counters("wire_match")
    c.increment("wire_held_total")
    assert c.snapshot()["wire_held_total"] == 1


def test_subledger_ic_match_counter():
    c = get_platform_counters("subledger_sync")
    c.increment("ic_matched_total")
    assert c.snapshot()["ic_matched_total"] == 1


def test_assetledger_negative_book_counter():
    c = get_platform_counters("asset_ledger")
    c.increment("negative_book_value_total")
    assert c.snapshot()["negative_book_value_total"] == 1


def test_credit_rail_attempt_counter():
    c = get_platform_counters("credit_govern")
    c.increment("rail_attempt_total")
    c.increment("rail_circuit_open_total")
    snap = c.snapshot()
    assert snap["rail_attempt_total"] == 1
    assert snap["rail_circuit_open_total"] == 1


def test_render_prometheus_text():
    from platforms.common.platform_metrics import render_prometheus_text

    get_platform_counters("wire_match").increment("wire_approved_total")
    text = render_prometheus_text("wire_match")
    assert "fg_platform_invariant_events_total" in text
    assert "wire_approved_total" in text
