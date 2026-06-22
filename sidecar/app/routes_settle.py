from fastapi import APIRouter, Depends, HTTPException, status

from .auth import require_internal_auth
from .config import get_settings
from .db import get_db_session
from .ledger import ConflictError, NotFoundError, PolicyStateError, apply_settlement
from .policy import PolicyDecisionError, validate_settle_request
from .schemas import SettleRequest, SettleResponse

router = APIRouter(tags=["settle"])


@router.post("/settle", response_model=SettleResponse, dependencies=[Depends(require_internal_auth)])
def settle(request: SettleRequest) -> SettleResponse:
    try:
        validate_settle_request(request)
        with get_db_session() as session:
            result = apply_settlement(session, get_settings(), request)
    except PolicyDecisionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (ConflictError, PolicyStateError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return SettleResponse(
        idempotency_key=result.idempotency_key,
        status=result.status,
        actual_amount=result.actual_amount,
    )
