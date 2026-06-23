from fastapi import APIRouter, Depends, HTTPException, status

from .auth import require_internal_auth
from .config import get_settings
from .db import get_db_session
from .orchestration import OrchestrationPolicyError, run_orchestration_workflow
from .schemas import OrchestrationWorkflowRequest, OrchestrationWorkflowResponse

router = APIRouter(tags=["orchestration"])


@router.post(
    "/orchestration/workflows/run",
    response_model=OrchestrationWorkflowResponse,
    dependencies=[Depends(require_internal_auth)],
)
def run_workflow(request: OrchestrationWorkflowRequest) -> OrchestrationWorkflowResponse:
    try:
        with get_db_session() as session:
            return run_orchestration_workflow(session, get_settings(), request)
    except OrchestrationPolicyError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
