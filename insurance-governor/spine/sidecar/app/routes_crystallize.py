from fastapi import APIRouter, Depends, HTTPException

from .auth import require_internal_auth
from .commit_ledger import (
    ConflictError,
    HorizonStrandedError,
    InsufficientReserveError,
    SurpriseCommitBlockedError,
    crystallize_operation,
)
from .config import get_settings
from .db import get_db_session
from .diagnostic_mode import is_diagnostic_mode
from .guardrail_errors import GuardrailError
from .circuit_breaker import CircuitOpenError
from .guardrails import get_guardrails
from .platform_guard import PlatformGuardError
from .schemas import CrystallizeRequest, CrystallizeResponse

router = APIRouter(tags=["crystallize"])


@router.post("/crystallize", response_model=CrystallizeResponse)
def crystallize(request: CrystallizeRequest, _: None = Depends(require_internal_auth)) -> CrystallizeResponse:
    if get_settings().diagnostic_mode_blocks_writes and is_diagnostic_mode():
        raise HTTPException(status_code=503, detail="diagnostic mode: writes halted")

    claim_id = str(request.facets.get("claim_id", request.operation_id))
    guardrails = get_guardrails()
    try:
        guardrails.check_crystallize(
            account_id=request.account_id,
            claim_id=claim_id,
            operation_id=request.operation_id,
        )
        with get_db_session() as session:
            from .platform_guard import assert_platform_allowed

            assert_platform_allowed(
                session,
                get_settings(),
                platform=request.platform,
                facets=request.facets,
            )
            result = crystallize_operation(
                session,
                get_settings(),
                platform=request.platform,
                operation_id=request.operation_id,
                account_id=request.account_id,
                risk_tier=request.risk_tier,
                facets=request.facets,
                policy_id=request.policy_id,
                reserved_reserve=request.reserved_reserve,
                parent_crystal_id=request.parent_crystal_id,
            )
    except GuardrailError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except CircuitOpenError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except PlatformGuardError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except InsufficientReserveError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    finally:
        guardrails.release_crystallize(account_id=request.account_id)

    return CrystallizeResponse(
        crystal_id=result.crystal_id,
        operation_id=result.operation_id,
        status=result.status,
        horizon_expires_at=result.horizon_expires_at,
    )
