from fastapi import Header, HTTPException, status


async def require_execution_identity(
    x_tenant_id: str | None = Header(default=None),
    x_session_id: str | None = Header(default=None),
    x_agent_run_id: str | None = Header(default=None),
    x_workflow_step: str | None = Header(default=None),
) -> dict[str, str]:
    if not x_tenant_id or not x_session_id or not x_agent_run_id or not x_workflow_step:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="missing execution identity headers",
        )
    return {
        "tenant_id": x_tenant_id,
        "session_id": x_session_id,
        "agent_run_id": x_agent_run_id,
        "workflow_step": x_workflow_step,
    }
