"""ZK claim commitment types — shared by persistence and zk_claim_audit platform."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ClaimCommitment:
    commitment_id: str
    claim_id: str
    commitment_hash: str
    salt: str
    fact_count: int
