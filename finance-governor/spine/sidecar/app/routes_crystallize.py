from fastapi import APIRouter, Depends, HTTPException, status

from .auth import require_internal_auth
from .commit_ledger import (
    ConflictError,
    HorizonStrandedError,
    InsufficientExposureError,
    SurpriseCommitBlockedError,
    crystallize_operation,
)
from .config import get_settings
from .db import get_db_session
from .diagnostic_mode import diagnostic_snapshot, is_diagnostic_mode
from .platform_registry import PlatformDisabledError, PlatformNotRegisteredError
from platforms.common.facet_schemas import FacetValidationError
from .schemas import CrystallizeRequest, CrystallizeResponse

router = APIRouter(tags=["crystallize"])


@router.post("/crystallize", response_model=CrystallizeResponse, dependencies=[Depends(require_internal_auth)])
def crystallize(request: CrystallizeRequest) -> CrystallizeResponse:
    if get_settings().diagnostic_mode_blocks_writes and is_diagnostic_mode():
        raise HTTPException(status_code=503, detail="diagnostic mode: writes halted")
    try:
        with get_db_session() as session:
            result = crystallize_operation(
                session,
                get_settings(),
                platform=request.platform,
                operation_id=request.operation_id,
                account_id=request.account_id,
                risk_tier=request.risk_tier,
                facets=request.facets,
                policy_id=request.policy_id,
                reserved_exposure=request.reserved_exposure,
                parent_crystal_id=request.parent_crystal_id,
            )
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except InsufficientExposureError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except PlatformNotRegisteredError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except PlatformDisabledError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except FacetValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return CrystallizeResponse(
        crystal_id=result.crystal_id,
        operation_id=result.operation_id,
        status=result.status,
        horizon_expires_at=result.horizon_expires_at,
    )
