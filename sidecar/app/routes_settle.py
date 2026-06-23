from fastapi import APIRouter, Depends, HTTPException, status

from .auth import require_internal_auth
from .config import get_settings
from .db import get_db_session
from .execution_identity import require_execution_identity
from .ledger import ConflictError, NotFoundError, PolicyStateError, apply_settlement
from .policy import PolicyDecisionError, validate_settle_request
from .schemas import SettleRequest, SettleResponse

router = APIRouter(tags=["settle"])


@router.post("/settle", response_model=SettleResponse, dependencies=[Depends(require_internal_auth)])
def settle(
    request: SettleRequest,
    identity: dict[str, str] = Depends(require_execution_identity),
) -> SettleResponse:
    try:
        _apply_identity(request, identity)
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


def _apply_identity(request: SettleRequest, identity: dict[str, str]) -> None:
    request.tenant_id = _bind_field(request.tenant_id, identity["tenant_id"], "tenant_id")
    request.session_id = _bind_field(request.session_id, identity["session_id"], "session_id")
    request.agent_run_id = _bind_field(request.agent_run_id, identity["agent_run_id"], "agent_run_id")
    request.workflow_step = _bind_field(request.workflow_step, identity["workflow_step"], "workflow_step")


def _bind_field(current: str | None, incoming: str, field_name: str) -> str:
    if current and current != incoming:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} in body does not match execution identity header",
        )
    return incoming
