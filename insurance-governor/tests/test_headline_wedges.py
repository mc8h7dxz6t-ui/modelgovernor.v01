from decimal import Decimal

import pytest

from platforms.spatial_twin.spatial_gate import evaluate_spatial_damage, hash_point_cloud
from platforms.spatial_twin.spatial_ingest import (
    attestation_hash,
    fetch_spatial_vendor_feed,
    normalize_spatial_vendor,
    verify_spatial_attestation,
)
from platforms.subrogation_graph.desk_ingest import (
    fetch_subro_desk_feed,
    normalize_subro_desk,
    verify_subro_attestation,
)
from platforms.subrogation_graph.graph_gate import evaluate_subrogation_graph


def test_battery_thermal_event_liability():
    from platforms.battery_liability.battery_gate import evaluate_battery_liability

    result = evaluate_battery_liability(
        claim_id="bat-1",
        state_of_health_pct=85.0,
        thermal_event=True,
        mileage=50_000,
        repair_estimate=Decimal("15000"),
    )
    assert result.approved is True
    assert result.decision == "APPROVED"


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
    assert result.net_damage == Decimal("50000")
    assert hash_point_cloud(1_000_000, {"x": 10.0, "y": 20.0}) == result.point_cloud_hash


def test_spatial_twin_held_over_coverage_limit():
    result = evaluate_spatial_damage(
        claim_id="sp-2",
        point_count=500_000,
        bounds={"x": 1.0, "y": 2.0},
        damage_estimate=Decimal("600000"),
        coverage_limit=Decimal("500000"),
        confidence=0.9,
    )
    assert result.decision == "HELD"
    assert result.reason == "exceeds_spatial_coverage"


def test_spatial_twin_referred_low_confidence():
    result = evaluate_spatial_damage(
        claim_id="sp-3",
        point_count=500_000,
        bounds={"x": 1.0, "y": 2.0},
        damage_estimate=Decimal("10000"),
        coverage_limit=Decimal("500000"),
        confidence=0.5,
    )
    assert result.decision == "REFERRED"
    assert result.reason == "low_vendor_confidence"


def test_spatial_twin_declined_below_deductible():
    result = evaluate_spatial_damage(
        claim_id="sp-4",
        point_count=500_000,
        bounds={"x": 1.0, "y": 2.0},
        damage_estimate=Decimal("1000"),
        coverage_limit=Decimal("500000"),
        deductible=Decimal("2500"),
        confidence=0.9,
    )
    assert result.decision == "DECLINED"
    assert result.net_damage == Decimal("0")


def test_spatial_vendor_feed_and_attestation():
    reading = fetch_spatial_vendor_feed()
    assert reading.point_count > 0
    assert verify_spatial_attestation(
        vendor=reading.vendor,
        payload=reading.payload,
        attestation_hash_value=reading.attestation_hash,
    )


def test_spatial_vendor_normalize():
    reading = normalize_spatial_vendor(
        "matterport-mock",
        {"scan": {"claim_id": "X-1", "point_count": 100_000, "damage_estimate": "12000", "confidence": 0.8}},
    )
    assert reading.claim_id == "X-1"
    assert reading.damage_estimate == Decimal("12000")


def test_subrogation_graph_recovery():
    result = evaluate_subrogation_graph(
        claim_id="sub-1",
        total_loss=Decimal("100000"),
        defendants={"carrier_a": 0.6, "carrier_b": 0.3},
    )
    assert result.recoverable is True
    assert result.primary_defendant == "carrier_a"
    assert result.recovery_amount == Decimal("60000.0")


def test_subrogation_graph_no_recovery_without_defendants():
    result = evaluate_subrogation_graph(
        claim_id="sub-2",
        total_loss=Decimal("100000"),
        defendants={},
    )
    assert result.decision == "NO_RECOVERY"


def test_subrogation_graph_salvage_offsets_recovery():
    result = evaluate_subrogation_graph(
        claim_id="sub-3",
        total_loss=Decimal("10000"),
        defendants={"carrier_a": 0.5},
        salvage_offset=Decimal("6000"),
    )
    assert result.decision == "NO_RECOVERY"
    assert result.reason == "salvage_offsets_recovery"


def test_subrogation_graph_statute_expired():
    result = evaluate_subrogation_graph(
        claim_id="sub-4",
        total_loss=Decimal("100000"),
        defendants={"carrier_a": 0.8},
        statute_expired=True,
    )
    assert result.decision == "REFERRED"
    assert result.reason == "statute_expired"


def test_subro_desk_feed_and_attestation():
    reading = fetch_subro_desk_feed()
    assert reading.defendants
    assert verify_subro_attestation(
        vendor=reading.vendor,
        payload=reading.payload,
        attestation_hash_value=reading.attestation_hash,
    )


def test_subro_desk_normalize_pro_rata():
    reading = normalize_subro_desk(
        "desk-mock",
        {"graph": {"claim_id": "G-1", "total_loss": "50000", "defendants": {"a": 0.8, "b": 0.8}}},
    )
    result = evaluate_subrogation_graph(
        claim_id=reading.claim_id,
        total_loss=reading.total_loss,
        defendants=reading.defendants,
    )
    assert result.decision == "RECOVERY_APPROVED"
