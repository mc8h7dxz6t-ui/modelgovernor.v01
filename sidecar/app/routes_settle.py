from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, Depends

from .auth import require_internal_auth
from .schemas import SettleRequest, SettleResponse

router = APIRouter(prefix="/v1/governance", tags=["settle"])


@router.post("/settle", response_model=SettleResponse, dependencies=[Depends(require_internal_auth)])
def settle_funds(request: SettleRequest) -> SettleResponse:
    # TODO: Implement transactional settlement lifecycle:
    # 1) lock ledger entry by wallet + idempotency key
    # 2) verify entry is in RESERVED state
    # 3) compute realized cost from authoritative provider usage
    # 4) set SETTLED state and release surplus funds to wallet
    # 5) append SETTLED_FINAL audit event (+ drift event if needed)

    settled_amount: Decimal = request.realized_cost

    return SettleResponse(
        ledger_entry_id=str(uuid4()),
        reservation_status="SETTLED",
        amount_settled=settled_amount,
        amount_released=Decimal("0"),
    )
