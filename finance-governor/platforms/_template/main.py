"""Platform template — copy to platforms/<your_platform>/ and customize."""
from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, Field

from platforms.common.platform_sdk import (
    CommitOutcome,
    PlatformConfig,
    create_platform_app,
    governed_operation,
    increment_invariant,
    spine_adapter_for,
)

CONFIG = PlatformConfig(
    name="template_platform",
    display_name="Template Platform",
    default_risk_tier="high",
    facet_schema={
        "required": ["operation_ref"],
        "properties": {
            "operation_ref": {"type": "string"},
            "amount": {"type": "string"},
        },
    },
    invariant_counters=("template_action_total",),
)

app = create_platform_app(CONFIG)
adapter = spine_adapter_for(CONFIG)


class EvaluateRequest(BaseModel):
    operation_ref: str
    amount: str = "0"


@app.post("/evaluate")
def evaluate(request: EvaluateRequest) -> dict:
    facets = {"operation_ref": request.operation_ref, "amount": request.amount}
    with governed_operation(adapter, request.operation_ref, facets) as ctx:
        approved = True
        if approved:
            adapter.commit(
                CommitOutcome(
                    operation_id=ctx.operation_id,
                    crystal_id=ctx.crystal_id,
                    facets=facets,
                    outcome="approved",
                    committed_exposure=request.amount,
                )
            )
            increment_invariant(CONFIG.name, "template_action_total")
    return {"operation_id": request.operation_ref, "crystal_id": ctx.crystal_id, "approved": approved}
