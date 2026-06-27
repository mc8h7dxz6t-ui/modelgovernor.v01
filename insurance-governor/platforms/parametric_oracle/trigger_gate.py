"""ParametricOracle — oracle-attested parametric trigger crystallization."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from decimal import Decimal

from platforms.common.crystal import canonical_fingerprint


@dataclass(frozen=True)
class TriggerEvaluation:
    triggered: bool
    decision: str
    reason: str | None
    score: float


def verify_oracle_attestation(*, source: str, payload: str, attestation_hash: str) -> bool:
    expected = hashlib.sha256(f"{source}:{payload}".encode()).hexdigest()
    return attestation_hash == expected


def evaluate_trigger(
    *,
    event_id: str,
    metric_value: Decimal,
    threshold: Decimal,
    oracle_verified: bool,
) -> TriggerEvaluation:
    if not oracle_verified:
        return TriggerEvaluation(triggered=False, decision="REJECTED", reason="oracle_unverified", score=0.0)
    if metric_value < threshold:
        return TriggerEvaluation(triggered=False, decision="BELOW_THRESHOLD", reason="metric_below_threshold", score=0.2)
    return TriggerEvaluation(triggered=True, decision="TRIGGERED", reason=None, score=1.0)


def trigger_facets(
    *,
    event_id: str,
    metric_value: Decimal,
    threshold: Decimal,
    oracle_source: str,
    attestation_hash: str,
    decision: str,
    score: float,
) -> dict:
    metric = str(metric_value)
    thresh = str(threshold)
    return {
        "event_id": event_id,
        "metric_value": metric,
        "threshold": thresh,
        "oracle_source": oracle_source,
        "oracle_attestation_hash": attestation_hash,
        "trigger_decision": decision,
        "trigger_score": score,
        "trigger_fingerprint": canonical_fingerprint(
            "parametric_oracle",
            event_id,
            {"metric": metric, "threshold": thresh, "oracle": oracle_source},
        ),
    }
