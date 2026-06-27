"""Shared oracle reading types."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class OracleReading:
    source: str
    metric_value: Decimal
    threshold: Decimal
    payload: str
    attestation_hash: str
    fetched_at: str


def attestation_hash(*, source: str, payload: str) -> str:
    return hashlib.sha256(f"{source}:{payload}".encode()).hexdigest()
