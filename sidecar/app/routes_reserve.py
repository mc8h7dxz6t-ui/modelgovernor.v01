from fastapi import APIRouter, Depends, HTTPException, status

from .auth import require_internal_auth
from .config import get_settings
from .db import get_db_session
from .ledger import (
    ConflictError,
    InsufficientFundsError,
    PolicyStateError,
    TraceCapExceededError,
    reserve_operation,
)
from .policy import PolicyDecisionError, validate_reserve_request
from .schemas import ReserveRequest, ReserveResponse

router = APIRouter(tags=["reserve"])


@router.post("/reserve", response_model=ReserveResponse, dependencies=[Depends(require_internal_auth)])
def reserve(request: ReserveRequest) -> ReserveResponse:
    try:
        validate_reserve_request(request)
        with get_db_session() as session:
            result = reserve_operation(session, get_settings(), request)
    except PolicyDecisionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except TraceCapExceededError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except InsufficientFundsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except PolicyStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return ReserveResponse(
        idempotency_key=result.idempotency_key,
        status=result.status,
        reserved_amount=request.estimated_cost,
        expires_in_seconds=get_settings().reserve_ttl_seconds,
    )
