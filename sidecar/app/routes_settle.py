from fastapi import APIRouter, Depends, HTTPException, status

from .auth import AuthContext, require_internal_auth
from .config import get_settings
from .db import get_tenant_db_session
from .diagnostic_mode import is_diagnostic_mode
from .enforcement_mode import execute_intercept_gate, policy_from_settings
from .governance_eval import evaluate_settle_governance
from .ledger import ConflictError, NotFoundError, PolicyStateError, apply_settlement
from .policy import PolicyDecisionError, validate_settle_request
from .schemas import SettleRequest, SettleResponse
from .tracing import span

router = APIRouter(tags=["settle"])


@router.post("/settle", response_model=SettleResponse)
def settle(
    request: SettleRequest,
    auth: AuthContext = Depends(require_internal_auth),
) -> SettleResponse:
    if get_settings().diagnostic_mode_blocks_writes and is_diagnostic_mode():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="diagnostic mode: settle writes halted; admin read APIs remain available",
        )
    try:
        validate_settle_request(request)
        with span(
            "settle_operation",
            {
                "idempotency_key": request.idempotency_key,
                "provider_request_id": request.provider_request_id,
            },
        ):
            policy = policy_from_settings()
            crystal_id = request.idempotency_key or request.provider_request_id or "settle"

            def _governance_eval() -> bool:
                with get_tenant_db_session(auth.tenant_id, commit=False) as session:
                    return evaluate_settle_governance(
                        session,
                        request,
                        auth_tenant_id=auth.tenant_id,
                    )

            gate = execute_intercept_gate(
                crystal_id=crystal_id,
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
