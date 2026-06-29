# Finance Governor Plug-and-Play

Finance Governor platforms are **deployable units** that work **standalone** or **spine-connected** with zero code changes — flip `FG_SPINE_ENABLED`.

## One-command paths

```bash
# Full L4 fleet + spine
cd finance-governor
make fg-demo-gold

# Certification (institutional++ → L4)
make fg-certification
make fg-certification-l4

# Platform SDK conformance
make fg-platform-conformance
```

## Add a new platform (5 steps)

1. **Copy template** — `platforms/_template/` → `platforms/my_platform/`
2. **Define contract** — `PlatformConfig` with facet schema + invariant counters
3. **Register** — migration row in `platform_registry` + optional `instrument_policy_registry` policy
4. **Deploy** — add to `values.yaml` `platforms.fleet` list (Helm) or compose service
5. **Certify** — `make fg-platform-conformance` + platform-specific invariant tests

## Helm fleet (generic)

Add any platform without editing templates:

```yaml
# values-enterprise.yaml
platforms:
  enabled: true
  fleet:
    - name: my_platform
      image: finance-governor-myplatform:0.4.0
      port: 8100
      replicas: 2
      enabled: true
```

```bash
helm template fg ./deploy/helm/finance-governor \
  -f values-production.yaml -f values-enterprise.yaml
```

## Spine discovery

| Endpoint | Service | Purpose |
|----------|---------|---------|
| `GET /internal/platforms` | sidecar | Registry catalog |
| `GET /platforms` | gateway | OIDC-gated fleet list |
| `POST /platforms/{name}/proxy/*` | gateway | Route to platform `base_url` |

## Reliability guarantees (institutional++)

| Guarantee | Mechanism |
|-----------|-----------|
| Pre-execution control | CCP crystallize before act |
| Tamper evidence | Hash-chained `decision_events` |
| Fail-closed registry | Unknown platform → 422 |
| Facet contract | Schema validation at crystallize |
| Deterministic recovery | `strand` + reconciler horizon sweep |
| Zero silent mutation | Append-only `platform_events` |
| HA deploy | PgBouncer, Sentinel, HPA (L4) |

## Related

- [platform-sdk.md](platform-sdk.md)
- [l4-certification.md](l4-certification.md)
- [operations-runbook.md](../../docs/finance-governor/operations-runbook.md)
