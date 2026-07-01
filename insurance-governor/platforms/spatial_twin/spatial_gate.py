"""LiDAR / photogrammetry spatial evidence gate — governed envelope (vendor connector = SOW)."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class SpatialEvaluation:
    approved: bool
    decision: str
    damage_estimate: Decimal
    net_damage: Decimal
    point_cloud_hash: str
    confidence: float
    reason: str | None


def hash_point_cloud(point_count: int, bounds: dict[str, float]) -> str:
    payload = f"{point_count}:{sorted(bounds.items())}"
    return hashlib.sha256(payload.encode()).hexdigest()


def evaluate_spatial_damage(
    *,
    claim_id: str,
    point_count: int,
    bounds: dict[str, float],
    damage_estimate: Decimal,
    coverage_limit: Decimal,
    min_confidence: float = 0.75,
    confidence: float = 0.85,
    deductible: Decimal = Decimal("0"),
    min_point_count: int = 10_000,
    max_scan_age_days: int = 90,
    scan_age_days: int = 0,
) -> SpatialEvaluation:
    del claim_id  # facet correlation via caller
    pch = hash_point_cloud(point_count, bounds)
    net = max(Decimal("0"), damage_estimate - deductible)

    if point_count < min_point_count:
        return SpatialEvaluation(False, "REFERRED", damage_estimate, net, pch, confidence, "insufficient_point_density")
    if scan_age_days > max_scan_age_days:
        return SpatialEvaluation(False, "REFERRED", damage_estimate, net, pch, confidence, "stale_scan")
    if confidence < min_confidence:
        return SpatialEvaluation(False, "REFERRED", damage_estimate, net, pch, confidence, "low_vendor_confidence")
    if net <= Decimal("0"):
        return SpatialEvaluation(False, "DECLINED", damage_estimate, net, pch, confidence, "below_deductible")
    if net > coverage_limit:
        return SpatialEvaluation(False, "HELD", damage_estimate, net, pch, confidence, "exceeds_spatial_coverage")
    return SpatialEvaluation(True, "APPROVED", damage_estimate, net, pch, confidence, None)
