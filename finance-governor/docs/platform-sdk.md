# Finance Governor Platform SDK

**Plug-and-play** integration for any finance domain platform — standalone or spine-connected at institutional++ grade.

## Quick start (new platform)

```python
from platforms.common.platform_sdk import (
    CommitOutcome,
    PlatformConfig,
    create_platform_app,
    governed_operation,
    increment_invariant,
    spine_adapter_for,
)

CONFIG = PlatformConfig(
    name="my_platform",
    display_name="My Platform",
    default_risk_tier="high",
    default_policy_id="my-policy-us",
    facet_schema={
        "required": ["operation_ref"],
        "properties": {"operation_ref": {"type": "string"}},
    },
    invariant_counters=("my_invariant_total",),
)

app = create_platform_app(CONFIG)
adapter = spine_adapter_for(CONFIG)

@app.post("/evaluate")
def evaluate(body: dict):
    op_id = body["operation_ref"]
    facets = {"operation_ref": op_id, "amount": body.get("amount", "0")}
    with governed_operation(adapter, op_id, facets, policy_id=CONFIG.default_policy_id) as ctx:
        approved = True  # domain logic here
        if approved:
            adapter.commit(
                CommitOutcome(
                    operation_id=ctx.operation_id,
                    crystal_id=ctx.crystal_id,
                    facets=facets,
                    outcome="approved",
                    committed_exposure=body.get("amount", "0"),
                )
            )
            increment_invariant(CONFIG.name, "my_invariant_total")
    return {"operation_id": op_id, "approved": approved}
```

## Deployment modes

| Mode | Env | Behavior |
|------|-----|----------|
| **Standalone** | `FG_SPINE_ENABLED=false` | Local CCP + `platform_events` audit; full value without spine |
| **Spine-connected** | `FG_SPINE_ENABLED=true` | Postgres-backed crystals, mesh rules, examiner export |

```bash
# Standalone
docker compose -f docker-compose.myplatform.yml up

# Spine-connected (add to finance-governor stack)
FG_SPINE_ENABLED=true FG_SIDECAR_URL=http://fg-sidecar:8091 docker compose up
```

## Spine contract

| Call | When | Fail-closed |
|------|------|-------------|
| `crystallize` | Before irreversible action | Registry + facet schema validated |
| `commit` | Terminal outcome | Fingerprint match, mesh, horizon |
| `strand` | Ambiguous / failed act | Manual or auto via `governed_operation` |

```python
adapter.strand(crystal_id, reason="compliance_hold")
```

## Platform registry

Register in Postgres (`platform_registry`) or via migration seed:

```sql
INSERT INTO platform_registry (
  platform_name, display_name, auth_token_hash, enabled,
  base_url, default_policy_id, facet_schema
) VALUES (
  'my_platform', 'My Platform', 'hash', TRUE,
  'http://fg-myplatform:8100', 'my-policy-us',
  '{"required":["operation_ref"],"properties":{"operation_ref":{"type":"string"}}}'::jsonb
);
```

Sidecar APIs:

- `GET /internal/platforms` — fleet catalog
- `GET /internal/platforms/{name}` — platform contract
- Gateway: `GET /platforms`, `POST /platforms/{name}/proxy/{path}`

## Institutional++ checklist

- [ ] `PlatformConfig` with facet schema + invariant counters
- [ ] `governed_operation` or explicit crystallize → commit
- [ ] `FG_SPINE_ENABLED=false` path tested
- [ ] `/healthz`, `/readyz`, `/metrics` via `create_platform_app`
- [ ] Idempotent `operation_id`
- [ ] Registry row + `instrument_policy_registry` policy
- [ ] `make fg-platform-conformance`

## Related

- [plug-and-play.md](plug-and-play.md)
- [platform-model.md](platform-model.md)
- [institutional-gold-standard.md](../../docs/finance-governor/institutional-gold-standard.md)
