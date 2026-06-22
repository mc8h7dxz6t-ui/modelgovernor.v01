from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import require_internal_auth
from app.config import get_settings
from app.policy import PolicyDecisionError, validate_reserve_request
from app.schemas import ReserveRequest, ReserveResponse

router = APIRouter(tags=["reserve"])


@router.post("/reserve", response_model=ReserveResponse, dependencies=[Depends(require_internal_auth)])
def reserve(request: ReserveRequest) -> ReserveResponse:
    try:
        validate_reserve_request(request)
    except PolicyDecisionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    settings = get_settings()

    return ReserveResponse(
        idempotency_key=request.idempotency_key,
        status="RESERVED",
        reserved_amount=request.estimated_cost,
        expires_in_seconds=settings.reserve_ttl_seconds,
    )
