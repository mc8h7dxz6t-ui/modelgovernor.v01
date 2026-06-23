# AI Cost Attribution and Agent Accountability

Institutional++ program for multi-dimensional spend attribution, agent identity, budget scopes, and accountability guardrails.

## Scope

- Execution identity (`tenant_id`, `session_id`, `agent_run_id`, `workflow_step`)
- Budget scopes: run, session, user, tenant (`budget_scope_state`)
- Guardrail incidents: manual approval, agent loop detection
- Execution lineage for audit and replay (`execution_lineage`)
- Attribution summary API by dimension

## Tests

```bash
pytest -q tests/programs/cost_attribution_accountability/
```

## APIs (internal auth)

- `GET /internal/attribution/summary?dimension=tenant|session|agent_run|workflow_step|user`
- `GET /internal/guardrail/incidents`
- `GET /internal/lineage/{idempotency_key}`

## Metrics

| Counter | Meaning |
|---|---|
| `budget_scope_exceeded_total` | Run/session/user/tenant cap denied |
| `guardrail_approval_required_total` | High-cost operation blocked pending approval |
| `agent_loop_detected_total` | Repeated loop signature guardrail |
| `attribution_identity_mismatch_total` | Settlement identity mismatch |
