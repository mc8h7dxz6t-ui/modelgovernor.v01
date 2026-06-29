"""Reserve route — guardrail inflight must release on failed reserve."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text

from .auth import require_internal_auth
from .config import get_settings
from .db import get_db_session
from .diagnostic_mode import diagnostic_snapshot, is_diagnostic_mode
from .guardrails import (
    GuardrailError,
    InflightLimitExceeded,
    RateLimitExceeded,
    TraceDepthExceeded,
    get_guardrails,
)
from .ledger import (
    ConflictError,
    InsufficientFundsError,
    PolicyStateError,
    TraceCapExceededError,
    reserve_operation,
)
from .policy import PolicyDecisionError, validate_reserve_request
from .schemas import ReserveRequest, ReserveResponse
from .tracing import span

router = APIRouter(tags=["reserve"])


def _idempotency_exists(idempotency_key: str) -> bool:
    with get_db_session() as session:
        row = session.execute(
            text("SELECT 1 FROM escrow_ledger WHERE idempotency_key = :k"),
            {"k": idempotency_key},
        ).first()
        return row is not None


@router.post("/reserve", response_model=ReserveResponse, dependencies=[Depends(require_internal_auth)])
def reserve(request: ReserveRequest) -> ReserveResponse:
    if get_settings().diagnostic_mode_blocks_writes and is_diagnostic_mode():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="diagnostic mode: reserve writes halted; admin read APIs remain available",
        )
    guardrail_bumped = False
    try:
        validate_reserve_request(request)
        with span(
            "reserve_operation",
            {
                "user_id": request.user_id,
                "trace_id": request.trace_id,
                "idempotency_key": request.idempotency_key,
                "model": request.model,
            },
        ):
            if not _idempotency_exists(request.idempotency_key):
                get_guardrails().check_reserve(
                    user_id=request.user_id,
                    trace_id=request.trace_id,
                    idempotency_key=request.idempotency_key,
                )
                guardrail_bumped = True
            with get_db_session() as session:
                result = reserve_operation(session, get_settings(), request)
    except PolicyDecisionError as exc:
        if guardrail_bumped:
            get_guardrails().release_reserve(user_id=request.user_id)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except (RateLimitExceeded, TraceDepthExceeded, InflightLimitExceeded) as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc
    except GuardrailError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc
    except ConflictError as exc:
        if guardrail_bumped:
            get_guardrails().release_reserve(user_id=request.user_id)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except TraceCapExceededError as exc:
        if guardrail_bumped:
            get_guardrails().release_reserve(user_id=request.user_id)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except InsufficientFundsError as exc:
        if guardrail_bumped:
            get_guardrails().release_reserve(user_id=request.user_id)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except PolicyStateError as exc:
        if guardrail_bumped:
            get_guardrails().release_reserve(user_id=request.user_id)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except Exception:
        if guardrail_bumped:
            get_guardrails().release_reserve(user_id=request.user_id)
        raise

    return ReserveResponse(
        idempotency_key=result.idempotency_key,
        status=result.status,
        reserved_amount=request.estimated_cost,
        expires_in_seconds=get_settings().reserve_ttl_seconds,
    )
