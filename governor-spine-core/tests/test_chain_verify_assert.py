"""Tests for shared chain verification assertions."""

from __future__ import annotations

import pytest

from spine_core.chain_verify_assert import assert_chain_verified


def test_assert_chain_verified_passes_when_fully_sealed() -> None:
    assert_chain_verified({"valid": True, "unsealed_count": 0})


def test_assert_chain_verified_rejects_invalid_chain() -> None:
    with pytest.raises(RuntimeError, match="chain invalid"):
        assert_chain_verified({"valid": False, "unsealed_count": 0})


def test_assert_chain_verified_rejects_unsealed_rows() -> None:
    with pytest.raises(RuntimeError, match="unsealed_count=2"):
        assert_chain_verified({"valid": True, "unsealed_count": 2})
