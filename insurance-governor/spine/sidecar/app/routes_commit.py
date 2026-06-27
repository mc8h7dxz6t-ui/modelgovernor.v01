from fastapi import APIRouter, Depends, HTTPException

from .auth import require_internal_auth
from .commit_ledger import HorizonStrandedError, SurpriseCommitBlockedError, commit_operation
from .config import get_settings
from .db import get_db_session
from .diagnostic_mode import is_diagnostic_mode
from .schemas import CommitRequest, CommitResponse

router = APIRouter(tags=["commit"])


@router.post("/commit", response_model=CommitResponse)
def commit(request: CommitRequest, _: None = Depends(require_internal_auth)) -> CommitResponse:
    if get_settings().diagnostic_mode_blocks_writes and is_diagnostic_mode():
        raise HTTPException(status_code=503, detail="diagnostic mode: writes halted")
    try:
        with get_db_session() as session:
            result = commit_operation(
                session,
                crystal_id=request.crystal_id,
                facets=request.facets,
                committed_reserve=request.committed_reserve,
                outcome=request.outcome,
                late_authority=request.late_authority,
            )
    except SurpriseCommitBlockedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except HorizonStrandedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return CommitResponse(
        operation_id=result.operation_id,
        crystal_id=result.crystal_id,
        status=result.status,
    )
