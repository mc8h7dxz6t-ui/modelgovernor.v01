"""Spatial vendor evidence ingest — mock photogrammetry connector (production LiDAR = SOW)."""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import httpx


@dataclass(frozen=True)
class SpatialVendorReading:
    vendor: str
    claim_id: str
    point_count: int
    bounds: dict[str, float]
    damage_estimate: Decimal
    confidence: float
    scan_age_days: int
    payload: str
    attestation_hash: str


def attestation_hash(*, vendor: str, payload: str) -> str:
    return hashlib.sha256(f"{vendor}:{payload}".encode()).hexdigest()


def normalize_spatial_vendor(vendor: str, payload: dict[str, Any]) -> SpatialVendorReading:
    data = payload.get("scan", payload)
    bounds = {k: float(v) for k, v in (data.get("bounds") or {"x": 0.0, "y": 0.0}).items()}
    return SpatialVendorReading(
        vendor=vendor,
        claim_id=str(data.get("claim_id", "unknown")),
        point_count=int(data.get("point_count", 0)),
        bounds=bounds,
        damage_estimate=Decimal(str(data.get("damage_estimate", "0"))),
        confidence=float(data.get("confidence", 0.85)),
        scan_age_days=int(data.get("scan_age_days", 0)),
        payload=json.dumps(payload, sort_keys=True),
        attestation_hash=attestation_hash(vendor=vendor, payload=json.dumps(payload, sort_keys=True)),
    )


def fetch_spatial_vendor_feed(vendor: str | None = None) -> SpatialVendorReading:
    vendor = vendor or os.environ.get("SPATIAL_VENDOR", "matterport-mock")
    url = os.environ.get("SPATIAL_VENDOR_URL")
    if url:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url)
            response.raise_for_status()
            return normalize_spatial_vendor(vendor, response.json())
    payload = {
        "scan": {
            "claim_id": "mock-spatial-1",
            "point_count": 750_000,
            "bounds": {"x": 12.5, "y": 8.0},
            "damage_estimate": "25000.00",
            "confidence": 0.88,
            "scan_age_days": 14,
        }
    }
    return normalize_spatial_vendor(vendor, payload)


def verify_spatial_attestation(*, vendor: str, payload: str, attestation_hash_value: str) -> bool:
    return attestation_hash(vendor=vendor, payload=payload) == attestation_hash_value
