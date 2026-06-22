from decimal import Decimal, ROUND_HALF_UP


SIX_DP = Decimal("0.000001")
MIN_RESERVE = Decimal("0.010000")
DEFAULT_ADAPTIVE_MULTIPLIER = Decimal("1.1000")
MAX_MULTIPLIER = Decimal("2.0000")


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(SIX_DP, rounding=ROUND_HALF_UP)


def compute_reservation_amount(
    estimated_cost: Decimal,
    adaptive_multiplier: Decimal = DEFAULT_ADAPTIVE_MULTIPLIER,
) -> Decimal:
    """Compute a policy-bounded reserve amount.

    Uses a bounded adaptive multiplier with conservative floor behavior:
    - multiplier clamped to [1.0, 2.0]
    - non-zero requests reserve at least a minimum floor
    """
    if estimated_cost <= 0:
        return Decimal("0")

    bounded_multiplier = max(Decimal("1.0"), min(adaptive_multiplier, MAX_MULTIPLIER))
    reserve = _quantize(estimated_cost * bounded_multiplier)
    return max(reserve, MIN_RESERVE)
