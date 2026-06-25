"""LiDAR spatial twin damage assessment gate."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class SpatialEvaluation:
    approved: bool
    decision: str
    damage_estimate: Decimal
    point_cloud_hash: str
    confidence: float
    reason: str | None


def hash_point_cloud(point_count: int, bounds: dict[str, float]) -> str:
    payload = f"{point_count}:{bounds}"
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
) -> SpatialEvaluation:
    pch = hash_point_cloud(point_count, bounds)
    if confidence < min_confidence:
        return SpatialEvaluation(False, "REFERRED", damage_estimate, pch, confidence, "low_lidar_confidence")
    if damage_estimate > coverage_limit:
        return SpatialEvaluation(False, "HELD", damage_estimate, pch, confidence, "exceeds_spatial_coverage")
    return SpatialEvaluation(True, "APPROVED", damage_estimate, pch, confidence, None)
