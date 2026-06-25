"""EV battery degradation and thermal liability gate."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class BatteryEvaluation:
    approved: bool
    decision: str
    liability_amount: Decimal
    reason: str | None


def evaluate_battery_liability(
    *,
    claim_id: str,
    state_of_health_pct: float,
    thermal_event: bool,
    mileage: int,
    repair_estimate: Decimal,
    soh_threshold: float = 70.0,
    max_mileage: int = 150_000,
) -> BatteryEvaluation:
    if thermal_event:
        return BatteryEvaluation(True, "APPROVED", repair_estimate, "thermal_event_confirmed")
    if state_of_health_pct < soh_threshold:
        return BatteryEvaluation(True, "APPROVED", repair_estimate, "degradation_below_threshold")
    if mileage > max_mileage:
        return BatteryEvaluation(False, "HELD", Decimal("0"), "mileage_exclusion")
    return BatteryEvaluation(False, "DECLINED", Decimal("0"), "no_battery_liability_trigger")
