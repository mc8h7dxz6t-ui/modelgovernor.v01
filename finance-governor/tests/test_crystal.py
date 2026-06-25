"""Tests for Crystal Commit Protocol core."""
from datetime import datetime, timedelta, timezone

from platforms.common.crystal import (
    is_horizon_expired,
    seal_crystal,
    should_strand_on_expiry,
    verify_commit_fingerprint,
)


def test_seal_crystal_deterministic_fingerprint():
    facets = {"deploy_sha": "abc123", "freeze_state": "ACTIVE"}
    c1 = seal_crystal(platform="algofreeze", operation_id="op-1", risk_tier="critical", facets=facets)
    c2 = seal_crystal(platform="algofreeze", operation_id="op-1", risk_tier="critical", facets=facets)
    assert c1.request_fingerprint == c2.request_fingerprint
    assert c1.crystal_id != c2.crystal_id


def test_verify_commit_fingerprint_match():
    facets = {"amount": "7800000.00", "currency": "USD"}
    crystal = seal_crystal(platform="wire_match", operation_id="wire-1", risk_tier="critical", facets=facets)
    assert verify_commit_fingerprint(crystal, facets) is True


def test_verify_commit_fingerprint_mismatch_blocks_surprise():
    facets = {"amount": "7800000.00", "currency": "USD"}
    crystal = seal_crystal(platform="wire_match", operation_id="wire-1", risk_tier="critical", facets=facets)
    assert verify_commit_fingerprint(crystal, {"amount": "900000000.00", "currency": "USD"}) is False


def test_critical_horizon_strands_not_guesses():
    assert should_strand_on_expiry("critical") is True
    assert should_strand_on_expiry("high") is True
    assert should_strand_on_expiry("standard") is False


def test_horizon_expiry():
    crystal = seal_crystal(
        platform="algofreeze",
        operation_id="op-2",
        risk_tier="critical",
        facets={},
        horizon_ms=1,
    )
    past = crystal.horizon_expires_at + timedelta(seconds=1)
    assert is_horizon_expired(crystal, now=past) is True
