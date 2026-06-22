from app.schemas import ReserveRequest, SettleRequest


class PolicyDecisionError(Exception):
    pass


def validate_reserve_request(request: ReserveRequest) -> None:
    if request.estimated_cost < 0:
        raise PolicyDecisionError("estimated_cost must be non-negative")


def validate_settle_request(request: SettleRequest) -> None:
    if request.actual_cost < 0:
        raise PolicyDecisionError("actual_cost must be non-negative")
