from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, Depends

from .auth import require_internal_auth
from .config import settings
from .schemas import ReserveRequest, ReserveResponse
from .policy import compute_reservation_amount

router = APIRouter(prefix="/v1/governance", tags=["reserve"])


@router.post("/reserve", response_model=ReserveResponse, dependencies=[Depends(require_internal_auth)])
def reserve_funds(request: ReserveRequest) -> ReserveResponse:
    reservation_amount: Decimal = compute_reservation_amount(request.estimated_cost)
    reserved_until = datetime.now(UTC) + timedelta(seconds=settings.default_reservation_ttl_seconds)

    # TODO: Implement transactional flow in Postgres:
    # 1) lock wallet row FOR UPDATE
    # 2) enforce idempotency via (wallet_id, idempotency_key)
    # 3) move available->reserved balances
    # 4) insert ledger_entries row with RESERVED status and expiry
    # 5) append audit_events RESERVE_CREATED

    return ReserveResponse(
        ledger_entry_id=str(uuid4()),
        reservation_status="RESERVED",
        amount_reserved=reservation_amount,
        reserved_until=reserved_until.isoformat(),
    )
