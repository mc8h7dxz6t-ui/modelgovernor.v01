"""Cross-platform mesh guard tests."""
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from platforms.common.mesh_guard import get_mesh_guard
from platforms.wire_match.execution_gate import evaluate_and_gate
from platforms.wire_match.semantic_matcher import GoldenRecord


def test_wire_blocked_when_algo_frozen():
    mesh = get_mesh_guard()
    golden = GoldenRecord("Revlon Lenders Group", "US12REV001", Decimal("7800000"))
    mesh.set_algo_active()
    ok = evaluate_and_gate(
        wire_id="w-mesh",
        beneficiary_name="Revlon Lenders Group",
        beneficiary_account="US12REV001",
        amount=Decimal("7800000"),
        golden=golden,
    )
    assert ok.decision == "APPROVED"

    mesh.set_algo_frozen("FEED_DEGRADED")
    try:
        blocked = evaluate_and_gate(
            wire_id="w-mesh-2",
            beneficiary_name="Revlon Lenders Group",
            beneficiary_account="US12REV001",
            amount=Decimal("7800000"),
            golden=golden,
        )
        assert blocked.decision == "HELD"
        assert "MESH_BLOCK" in (blocked.reason or "")
    finally:
        mesh.set_algo_active()
