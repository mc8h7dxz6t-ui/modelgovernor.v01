from decimal import Decimal

from platforms.battery_liability.battery_gate import evaluate_battery_liability
from platforms.spatial_twin.spatial_gate import evaluate_spatial_damage, hash_point_cloud
from platforms.subrogation_graph.graph_gate import evaluate_subrogation_graph


def test_spatial_twin_approves_within_limit():
    result = evaluate_spatial_damage(
        claim_id="sp-1",
        point_count=1_000_000,
        bounds={"x": 10.0, "y": 20.0},
        damage_estimate=Decimal("50000"),
        coverage_limit=Decimal("500000"),
        confidence=0.9,
    )
    assert result.decision == "APPROVED"
    assert hash_point_cloud(1_000_000, {"x": 10.0, "y": 20.0}) == result.point_cloud_hash


def test_battery_thermal_event_liability():
    result = evaluate_battery_liability(
        claim_id="bat-1",
        state_of_health_pct=85.0,
        thermal_event=True,
        mileage=50_000,
        repair_estimate=Decimal("15000"),
    )
    assert result.approved is True
    assert result.decision == "APPROVED"


def test_subrogation_graph_recovery():
    result = evaluate_subrogation_graph(
        claim_id="sub-1",
        total_loss=Decimal("100000"),
        defendants={"carrier_a": 0.6, "carrier_b": 0.3},
    )
    assert result.recoverable is True
    assert result.primary_defendant == "carrier_a"
    assert result.recovery_amount == Decimal("60000.0")
