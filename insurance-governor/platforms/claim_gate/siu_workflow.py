"""SIU referral workflow — fraud signal aggregation and referral lifecycle."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class SiuState(str, Enum):
    CLEARED = "CLEARED"
    REFERRED = "REFERRED"
    BLOCKED = "BLOCKED"
    UNDER_REVIEW = "UNDER_REVIEW"


# Industry-standard fraud signal taxonomy (subset)
FRAUD_SIGNAL_WEIGHTS: dict[str, float] = {
    "duplicate_claim": 0.35,
    "inconsistent_statement": 0.25,
    "staged_loss_pattern": 0.40,
    "medical_provider_alert": 0.30,
    "geographic_anomaly": 0.20,
    "siu_referral": 1.0,
    "prior_fraud_conviction": 0.50,
    "late_reporting": 0.15,
}


@dataclass
class SiuReferral:
    referral_id: str
    claim_id: str
    state: SiuState
    fraud_score: float
    signals: list[str]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    analyst_notes: str | None = None


def score_fraud_signals(signals: list[str]) -> float:
    if not signals:
        return 0.0
    total = sum(FRAUD_SIGNAL_WEIGHTS.get(s, 0.10) for s in signals)
    return min(1.0, total)


def evaluate_siu(
    *,
    claim_id: str,
    signals: list[str],
    siu_flag: bool = False,
    threshold_refer: float = 0.35,
    threshold_block: float = 0.70,
) -> SiuReferral:
    manual_refer = siu_flag and not signals
    if siu_flag and "siu_referral" not in signals:
        signals = [*signals, "siu_referral"]

    if manual_refer:
        return SiuReferral(
            referral_id=f"siu_{uuid.uuid4().hex[:12]}",
            claim_id=claim_id,
            state=SiuState.REFERRED,
            fraud_score=threshold_refer,
            signals=signals,
        )

    score = score_fraud_signals(signals)

    if score >= threshold_block:
        state = SiuState.BLOCKED
    elif score >= threshold_refer:
        state = SiuState.REFERRED
    else:
        state = SiuState.CLEARED

    return SiuReferral(
        referral_id=f"siu_{uuid.uuid4().hex[:12]}",
        claim_id=claim_id,
        state=state,
        fraud_score=round(score, 4),
        signals=signals,
    )
