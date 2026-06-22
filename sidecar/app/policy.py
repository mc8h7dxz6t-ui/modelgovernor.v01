from .schemas import ReserveRequest, SettleRequest


class PolicyDecisionError(Exception):
    pass


def validate_reserve_request(request: ReserveRequest) -> None:
    if request.estimated_cost < 0:
        raise PolicyDecisionError("estimated_cost must be non-negative")
    if request.trace_cap is not None and request.trace_cap <= 0:
        raise PolicyDecisionError("trace_cap must be positive when provided")


def validate_settle_request(request: SettleRequest) -> None:
    if request.actual_cost < 0:
        raise PolicyDecisionError("actual_cost must be non-negative")
    if not request.idempotency_key and not request.provider_request_id:
        raise PolicyDecisionError("either idempotency_key or provider_request_id is required")
    if request.outcome != "SETTLED" and not request.dispatch_attempt_key:
        raise PolicyDecisionError("dispatch_attempt_key is required for non-terminal updates")
    if request.outcome == "SETTLED" and request.actual_cost < 0:
        raise PolicyDecisionError("actual_cost must be non-negative")
