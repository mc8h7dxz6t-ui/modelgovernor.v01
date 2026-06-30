"""Tests for shared attestation validation."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from spine_core.attestation_validate import load_cluster_attestation, phase_c_valid, validate_cluster_attestation


def test_stub_attestation_rejected(tmp_path: Path):
    path = tmp_path / "cluster_attestation.json"
    path.write_text(json.dumps({"probes_note": "stub", "probes_total": 8, "probes_passed": 8}))
    errors = validate_cluster_attestation(load_cluster_attestation(path))
    assert any("stub" in e for e in errors)
    assert phase_c_valid(path) is False


def test_valid_attestation_accepted(tmp_path: Path):
    path = tmp_path / "cluster_attestation.json"
    payload = {
        "probes_total": 8,
        "probes_passed": 8,
        "artifact_sha256": "a" * 64,
        "environment": "customer-vpc-staging",
        "probes": [{"name": "p1", "status": "pass"}] * 8,
    }
    path.write_text(json.dumps(payload))
    assert validate_cluster_attestation(load_cluster_attestation(path)) == []
    assert phase_c_valid(path) is True


def test_embedded_rehearsal_rejected(tmp_path: Path):
    path = tmp_path / "cluster_attestation.json"
    payload = {
        "probes_total": 7,
        "probes_passed": 7,
        "artifact_sha256": "c" * 64,
        "environment": "local-embedded-rehearsal",
        "probes": [{"name": "p1", "status": "pass"}] * 7,
    }
    path.write_text(json.dumps(payload))
    assert phase_c_valid(path) is False


def test_ci_mock_environment_rejected(tmp_path: Path):
    path = tmp_path / "cluster_attestation.json"
    payload = {
        "probes_total": 8,
        "probes_passed": 8,
        "artifact_sha256": "b" * 64,
        "environment": "ci-mock",
        "probes": [{"name": "p1", "status": "pass"}],
    }
    path.write_text(json.dumps(payload))
    assert phase_c_valid(path) is False
