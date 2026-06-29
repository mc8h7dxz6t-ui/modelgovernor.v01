"""Bias cohort monitoring hooks — institutional++ fairness signals."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from .platform_metrics import get_platform_counters


@dataclass(frozen=True)
class CohortObservation:
    cohort_key: str
    application_id: str
    score: float
    decision: str
    metadata: dict[str, Any]


def record_credit_cohort(
    *,
    platform: str,
    desk_id: str,
    model_version_id: str,
    application_id: str,
    score: float,
    decision: str,
    exposure: Decimal,
    protected_attributes: dict[str, str] | None = None,
) -> CohortObservation:
    """Record cohort observation and emit BIAS_ALERT counter on material skew heuristic."""
    cohort_key = f"{desk_id}:{model_version_id}"
    meta = {
        "desk_id": desk_id,
        "model_version_id": model_version_id,
        "exposure": str(exposure),
        "protected_attributes": protected_attributes or {},
    }
    obs = CohortObservation(
        cohort_key=cohort_key,
        application_id=application_id,
        score=score,
        decision=decision,
        metadata=meta,
    )
    counters = get_platform_counters(platform)
    if decision == "APPROVE" and score < 0.5:
        counters.increment("bias_cohort_alert_total")
    elif decision == "REFER" and score > 0.9:
        counters.increment("bias_cohort_alert_total")
    return obs
