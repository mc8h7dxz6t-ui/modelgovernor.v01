# Insurance Governor — Platform Model

Each platform is a **deployable unit** that functions alone or plugs into the optional spine.

## Design principle

```
┌─────────────────────────────────────────────────────────────────┐
│              OPTIONAL: Insurance Governor Spine                  │
│  Gateway │ Sidecar │ Reconciler │ Hash Chain │ claim_ops        │
└───────────────────────────────┬─────────────────────────────────┘
                                │ SpineAdapter (IG_SPINE_ENABLED)
        ┌───────────┬───────────┼───────────┬───────────┐
        ▼           ▼           ▼           ▼           ▼
   ClaimGate   ZkClaimAudit SpatialTwin BatteryLiab SubrogationGraph
   (standalone) (standalone) (standalone) (standalone)  (standalone)
```

## Extracting a platform

Each `platforms/<name>/` directory is self-contained:

| Artifact | Purpose |
|----------|---------|
| `Dockerfile` | Single-service image |
| `docker-compose.standalone.yml` | No spine dependencies |
| `main.py` | FastAPI gate API |
| `README.md` | Platform invariants + runbook |

Copy `platforms/common/` alongside the platform — it has zero spine dependency.

## Spine integration contract

```python
from platforms.common.spine_adapter import CommitOutcome, SpineAdapter

adapter = SpineAdapter(platform="claim_gate", spine_enabled=os.environ.get("IG_SPINE_ENABLED") == "true")
crystal = adapter.crystallize(operation_id, risk_tier, facets, policy_id=...)
adapter.commit(CommitOutcome(...))
```

When `IG_SPINE_ENABLED=false`:
- Crystals stored in `LocalCrystalStore`
- Events appended to `LocalPlatformEventLog` (SQLite)
- **No functionality loss** — only unified cross-platform examiner view

## Environment variables

| Variable | Standalone | Spine-connected |
|----------|------------|-----------------|
| `IG_SPINE_ENABLED` | `false` | `true` |
| `IG_SIDECAR_URL` | ignored | `http://ig-sidecar:8101` |
| `IG_INTERNAL_TOKEN` | ignored | shared secret |
| `IG_PLATFORM_EVENTS_DB` | optional path | ignored |

## Anti-patterns

- Requiring spine for platform to function
- Platform logic inside sidecar (spine stays domain-agnostic)
- Shared mutable state between platforms (only spine events)
