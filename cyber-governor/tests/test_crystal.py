"""Tests for Threat Crystal Protocol core."""
from datetime import timedelta

from platforms.common.threat_crystal import (
    is_horizon_expired,
    seal_crystal,
    should_strand_on_expiry,
    verify_commit_fingerprint,
)


def test_seal_crystal_deterministic_fingerprint():
    facets = {"device_fingerprint": "dev_fp_trusted", "session_state": "AUTHORIZED"}
    c1 = seal_crystal(platform="identity_gate", operation_id="op-1", risk_tier="critical", facets=facets)
    c2 = seal_crystal(platform="identity_gate", operation_id="op-1", risk_tier="critical", facets=facets)
    assert c1.request_fingerprint == c2.request_fingerprint
    assert c1.crystal_id != c2.crystal_id
    assert c1.crystal_id.startswith("tcrys_")


def test_verify_commit_fingerprint_match():
    facets = {"destination": "s3://corp-backup", "byte_count": 1024}
    crystal = seal_crystal(platform="egress_lock", operation_id="eg-1", risk_tier="critical", facets=facets)
    assert verify_commit_fingerprint(crystal, facets) is True


def test_verify_commit_fingerprint_mismatch_blocks_surprise():
    facets = {"destination": "s3://corp-backup", "byte_count": 1024}
    crystal = seal_crystal(platform="egress_lock", operation_id="eg-1", risk_tier="critical", facets=facets)
    assert verify_commit_fingerprint(crystal, {"destination": "evil-exfil.example", "byte_count": 999999}) is False


def test_critical_horizon_strands_not_guesses():
    assert should_strand_on_expiry("critical") is True
    assert should_strand_on_expiry("high") is True
    assert should_strand_on_expiry("standard") is False


def test_horizon_expiry():
    crystal = seal_crystal(
        platform="witness_bridge",
        operation_id="op-2",
        risk_tier="critical",
        facets={},
        horizon_ms=1,
    )
    past = crystal.horizon_expires_at + timedelta(seconds=1)
    assert is_horizon_expired(crystal, now=past) is True
