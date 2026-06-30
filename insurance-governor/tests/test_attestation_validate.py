"""Tests for attestation publish validation."""
from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import attestation_validate as av  # noqa: E402


def test_validate_rejects_stub_attestation():
    stub = {
        "probes_note": "stub",
        "certification": True,
    }
    try:
        av.validate_cluster_attestation(stub)
        assert False, "expected SystemExit"
    except SystemExit as exc:
        assert "stub" in str(exc).lower()


def test_validate_accepts_live_shape():
    live = {
        "probes_total": 7,
        "probes_passed": 7,
        "artifact_sha256": "a" * 64,
        "probes": [{"name": "spine_ready", "status": "pass"}],
        "environment": "customer-vpc-staging",
    }
    av.validate_cluster_attestation(live, min_passed=7)
