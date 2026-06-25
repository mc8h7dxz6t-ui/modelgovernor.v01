# Insurance Governor — Platform Model

Each platform is a **deployable unit** that functions alone or plugs into the optional spine via a **standard SDK contract**.

## Plug-and-play contract

```
platforms/<name>/
├── manifest.yaml          # Registry contract (required facets, commit decisions, policy)
├── main.py                # FastAPI service using GovernedPlatform
├── Dockerfile
└── docker-compose.standalone.yml
```

Register in `platforms/registry.yaml` + spine migration (`platform_registry` + `coverage_policy_registry`).

## SDK usage (any platform)

```python
from platforms.common.platform_sdk import GovernedPlatform, spine_health_payload

_GOVERNED = GovernedPlatform("my_platform")  # loads manifest.yaml

crystal_id = _GOVERNED.govern_operation(
    operation_id,
    facets,
    decision="APPROVED",       # must be in manifest commit_decisions to commit
    reserve_amount="1000.00",
    account_id="carrier-default",
    policy_id="my-policy-us",  # optional — defaults from manifest
    outcome="paid",
)
```

## Spine integration

| Mode | `IG_SPINE_ENABLED` | Behavior |
|------|-------------------|----------|
| Standalone | `false` | LocalCrystalStore + LocalPlatformEventLog |
| Spine-connected | `true` | HTTP crystallize/commit via sidecar |

Spine enforces **platform registry** (`platform_registry_enforce=true`):
- Platform must be registered and enabled
- Required facet keys from `manifest_json` must be present
- Rejects with 422 before any reserve mutation

## Scaffold a new platform

```bash
insurance-governor/scripts/scaffold-platform.sh my_platform 8110
```

Then:
1. Add entry to `platforms/registry.yaml`
2. Add policy + registry rows in migration SQL
3. Add Helm `values.platforms.my_platform` block (plug-and-play deploy)

## Anti-patterns

- Bypassing `GovernedPlatform` for commits
- Hardcoding spine URLs without `SpineAdapter`
- Skipping manifest `required_facet_keys` (spine will reject)
- Platform logic inside sidecar (spine stays domain-agnostic)

## Environment variables

| Variable | Standalone | Spine-connected |
|----------|------------|-----------------|
| `IG_SPINE_ENABLED` | `false` | `true` |
| `IG_SIDECAR_URL` | ignored | `http://sidecar:8101` |
| `IG_INTERNAL_TOKEN` | ignored | shared secret |
| `PLATFORM_REGISTRY_ENFORCE` | sidecar only | `true` in production |
