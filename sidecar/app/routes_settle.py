from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import require_internal_auth
from app.policy import PolicyDecisionError, validate_settle_request
from app.schemas import SettleRequest, SettleResponse

router = APIRouter(tags=["settle"])


@router.post("/settle", response_model=SettleResponse, dependencies=[Depends(require_internal_auth)])
def settle(request: SettleRequest) -> SettleResponse:
    try:
        validate_settle_request(request)
    except PolicyDecisionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return SettleResponse(
        idempotency_key=request.idempotency_key,
        status="SETTLED",
        actual_amount=request.actual_cost,
    )
