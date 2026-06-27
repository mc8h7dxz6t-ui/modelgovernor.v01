from fastapi import APIRouter, Depends, HTTPException, status

from .auth import AuthContext, require_internal_auth
from .config import get_settings
from .db import get_tenant_db_session
from .diagnostic_mode import diagnostic_snapshot, is_diagnostic_mode
from .enforcement_mode import execute_intercept_gate, policy_from_settings
from .governance_eval import evaluate_reserve_governance
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


@router.post("/reserve", response_model=ReserveResponse)
def reserve(
    request: ReserveRequest,
    auth: AuthContext = Depends(require_internal_auth),
) -> ReserveResponse:
    if get_settings().diagnostic_mode_blocks_writes and is_diagnostic_mode():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="diagnostic mode: reserve writes halted; admin read APIs remain available",
        )
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
            get_guardrails().check_reserve(
                user_id=request.user_id,
                trace_id=request.trace_id,
                idempotency_key=request.idempotency_key,
            )

            policy = policy_from_settings()

            def _governance_eval() -> bool:
                with get_tenant_db_session(auth.tenant_id, commit=False) as session:
                    return evaluate_reserve_governance(
                        session,
                        request,
                        auth_tenant_id=auth.tenant_id,
                    )

            gate = execute_intercept_gate(
                crystal_id=request.idempotency_key,
                tenant_id=auth.tenant_id,
                domain="MODEL_GOV",
                policy=policy,
                core_validation=_governance_eval,
            )
            if gate.action == "DENY":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=gate.reason or "governor intercept deny",
                )

            with get_tenant_db_session(auth.tenant_id) as session:
                result = reserve_operation(session, get_settings(), request)
    except PolicyDecisionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except (RateLimitExceeded, TraceDepthExceeded, InflightLimitExceeded) as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc
    except GuardrailError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc
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
