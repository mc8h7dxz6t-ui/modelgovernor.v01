from decimal import Decimal


def compute_reservation_amount(estimated_cost: Decimal) -> Decimal:
    """Return reserve amount for reserve-before-dispatch workflow.

    TODO: Replace this conservative placeholder with policy-bounded adaptive sizing logic
    that considers cohort confidence intervals and drift fallback signals.
    """
    return estimated_cost
