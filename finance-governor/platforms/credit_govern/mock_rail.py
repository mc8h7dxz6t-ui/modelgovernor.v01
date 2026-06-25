"""Mock credit inference rail (bureau/model stand-in)."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ScoreResult:
    score: Decimal
    risk_tier: str
    explanation_id: str


class MockCreditRail:
    def score(self, *, feature_snapshot_hash: str) -> ScoreResult:
        digest = int(hashlib.sha256(feature_snapshot_hash.encode()).hexdigest()[:8], 16)
        normalized = Decimal(digest % 1000) / Decimal(1000)
        risk = "high" if normalized > Decimal("0.85") else "low"
        explanation_id = hashlib.sha256(f"explain:{feature_snapshot_hash}".encode()).hexdigest()[:16]
        return ScoreResult(score=normalized, risk_tier=risk, explanation_id=explanation_id)
