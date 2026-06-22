from decimal import Decimal, ROUND_HALF_UP

from app.schemas import (
    ProviderAdjustmentRequest,
    ProviderReconciliationRequest,
    ReserveRequest,
    SettleRequest,
)

MONEY_QUANTUM = Decimal("0.000001")
MINIMUM_RESERVE = Decimal("0.010000")
MAX_RESERVE_MULTIPLIER = Decimal("1.250000")


class PolicyDecisionError(Exception):
    pass


def quantize_money(amount: Decimal) -> Decimal:
    return amount.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def calculate_reserve_amount(estimated_cost: Decimal) -> Decimal:
    normalized_cost = quantize_money(estimated_cost)
    if normalized_cost < 0:
        raise PolicyDecisionError("estimated_cost must be non-negative")

    bounded_reserve = quantize_money(normalized_cost * MAX_RESERVE_MULTIPLIER)
    return max(bounded_reserve, MINIMUM_RESERVE)


def validate_reserve_request(request: ReserveRequest) -> None:
    if quantize_money(request.estimated_cost) < 0:
        raise PolicyDecisionError("estimated_cost must be non-negative")



def validate_settle_request(request: SettleRequest) -> None:
    if quantize_money(request.actual_cost) < 0:
        raise PolicyDecisionError("actual_cost must be non-negative")


def validate_provider_reconciliation_request(request: ProviderReconciliationRequest) -> None:
    if quantize_money(request.provider_actual_cost) < 0:
        raise PolicyDecisionError("provider_actual_cost must be non-negative")
    if not request.idempotency_key and not request.provider_request_id:
        raise PolicyDecisionError("idempotency_key or provider_request_id is required")


def validate_provider_adjustment_request(request: ProviderAdjustmentRequest) -> None:
    if not request.reason.strip():
        raise PolicyDecisionError("reason must not be blank")
