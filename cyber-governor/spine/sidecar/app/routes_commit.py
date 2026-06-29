from fastapi import APIRouter, Depends, HTTPException

from .auth import require_internal_auth
from .commit_ledger import HorizonStrandedError, SurpriseCommitBlockedError, commit_operation
from .config import get_settings
from .db import get_db_session
from .diagnostic_mode import is_diagnostic_mode
from .schemas import CommitRequest, CommitResponse

router = APIRouter(tags=["commit"])


@router.post("/commit", response_model=CommitResponse, dependencies=[Depends(require_internal_auth)])
def commit(request: CommitRequest) -> CommitResponse:
    if get_settings().diagnostic_mode_blocks_writes and is_diagnostic_mode():
        raise HTTPException(status_code=503, detail="diagnostic mode: writes halted")
    try:
        with get_db_session() as session:
            result = commit_operation(
                session,
                crystal_id=request.crystal_id,
                facets=request.facets,
                committed_exposure=request.committed_exposure,
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
