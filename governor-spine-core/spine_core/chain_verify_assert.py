"""Shared chain verification assertions for attestation and smoke gates."""

from __future__ import annotations

from typing import Any


def assert_chain_verified(result: dict[str, Any], *, context: str = "verify-chain") -> None:
    if not result.get("valid"):
        raise RuntimeError(f"{context}: chain invalid: {result}")
    unsealed = int(result.get("unsealed_count") or 0)
    if unsealed != 0:
        raise RuntimeError(f"{context}: unsealed_count={unsealed}: {result}")
