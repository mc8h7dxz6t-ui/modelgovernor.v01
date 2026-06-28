"""HTTP tests for SpatialTwin and SubrogationGraph wedges."""
from __future__ import annotations

import os

os.environ.setdefault("IG_SPINE_ENABLED", "false")

from fastapi.testclient import TestClient

from platforms.spatial_twin.main import app as spatial_app
from platforms.spatial_twin.spatial_ingest import fetch_spatial_vendor_feed
from platforms.subrogation_graph.desk_ingest import fetch_subro_desk_feed
from platforms.subrogation_graph.main import app as subro_app


def test_spatial_feed_endpoint():
    client = TestClient(spatial_app)
    response = client.get("/spatial/feed")
    assert response.status_code == 200
    body = response.json()
    assert body["vendor_attestation_hash"]
    assert body["point_count"] > 0


def test_spatial_evaluate_approved():
    client = TestClient(spatial_app)
    response = client.post(
        "/spatial/evaluate",
        json={
            "claim_id": "http-sp-1",
            "point_count": 500_000,
            "bounds": {"x": 1.0, "y": 2.0},
            "damage_estimate": "15000.00",
            "confidence": 0.9,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "APPROVED"
    assert "crystal_id" in body


def test_spatial_evaluate_attestation_mismatch():
    client = TestClient(spatial_app)
    reading = fetch_spatial_vendor_feed()
    response = client.post(
        "/spatial/evaluate",
        json={
            "claim_id": "http-sp-2",
            "point_count": reading.point_count,
            "bounds": reading.bounds,
            "damage_estimate": str(reading.damage_estimate),
            "confidence": reading.confidence,
            "vendor": reading.vendor,
            "vendor_payload": reading.payload,
            "vendor_attestation_hash": "0" * 64,
        },
    )
    assert response.status_code == 422


def test_subro_feed_endpoint():
    client = TestClient(subro_app)
    response = client.get("/subrogation/feed")
    assert response.status_code == 200
    assert response.json()["defendants"]


def test_subro_evaluate_recovery():
    client = TestClient(subro_app)
    response = client.post(
        "/subrogation/evaluate",
        json={
            "claim_id": "http-sub-1",
            "total_loss": "100000.00",
            "defendants": {"carrier_a": 0.55},
        },
    )
    assert response.status_code == 200
    assert response.json()["decision"] == "RECOVERY_APPROVED"


def test_subro_evaluate_with_verified_attestation():
    client = TestClient(subro_app)
    reading = fetch_subro_desk_feed()
    response = client.post(
        "/subrogation/evaluate",
        json={
            "claim_id": reading.claim_id,
            "total_loss": str(reading.total_loss),
            "defendants": reading.defendants,
            "salvage_offset": str(reading.salvage_offset),
            "vendor": reading.vendor,
            "vendor_payload": reading.payload,
            "vendor_attestation_hash": reading.attestation_hash,
        },
    )
    assert response.status_code == 200
    assert response.json()["decision"] == "RECOVERY_APPROVED"
