from fastapi import APIRouter, Depends, HTTPException

from .auth import require_internal_auth
from .commit_ledger import SurpriseCommitBlockedError, adjudicate_operation
from .config import get_settings
from .db import get_db_session
from .diagnostic_mode import is_diagnostic_mode
from .schemas import AdjudicateRequest, AdjudicateResponse

router = APIRouter(tags=["adjudicate"])


@router.post("/adjudicate", response_model=AdjudicateResponse, dependencies=[Depends(require_internal_auth)])
def adjudicate(request: AdjudicateRequest) -> AdjudicateResponse:
    if get_settings().diagnostic_mode_blocks_writes and is_diagnostic_mode():
        raise HTTPException(status_code=503, detail="diagnostic mode: writes halted")
    try:
        with get_db_session() as session:
            result = adjudicate_operation(
                session,
                crystal_id=request.crystal_id,
                action=request.action,
                reason=request.reason,
            )
    except SurpriseCommitBlockedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return AdjudicateResponse(
        operation_id=result.operation_id,
        crystal_id=result.crystal_id,
        status=result.status,
    )
