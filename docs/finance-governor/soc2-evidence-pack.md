# SOC 2 Type II Evidence Pack (Finance Governor)

Map Finance Governor artifacts to common SOC 2 Trust Services Criteria. Use with FG-ECP attestation reports in auditor data rooms.

## CC6 — Logical access

| Control | Evidence |
|---------|----------|
| OIDC gateway termination | `values-production.yaml` `oidc.enabled` |
| RBAC on sidecar admin routes | `routes_admin.py` `require_financial_admin` |
| Internal token segregation | `FG_INTERNAL_TOKEN` / ExternalSecrets |

**Proof:** `pytest tests/test_auth_oidc.py` · Helm render with `oidc.enabled: true`

## CC7 — System operations

| Control | Evidence |
|---------|----------|
| Diagnostic mode (no poison pill) | `test_diagnostic_mode.py` |
| Invariant counters | `/metrics` · `PrometheusRule` |
| Chain verification CronJob | `decisionChainVerify` |

**Proof:** `make fg-certification-l4` · `GET /internal/decisions/verify-chain`

## CC8 — Change management

| Control | Evidence |
|---------|----------|
| GitOps manifests | `deploy/argocd/` |
| Helm versioned chart | `Chart.yaml` |
| CI gates | `.github/workflows/fg-ci.yml` |

**Proof:** ArgoCD Application manifest · CI green on merge

## CC9 — Risk mitigation

| Control | Evidence |
|---------|----------|
| Pre-execution crystallize | CCP on all platforms |
| Exposure caps + drift | `test_exposure_drift.py` |
| Chaos harness | `tests/chaos/test_toxiproxy_fg_spine.py` |

## A1 — Availability

| Control | Evidence |
|---------|----------|
| HPA, PDB, anti-affinity | `values-enterprise.yaml` |
| PgBouncer + RDS overlay | `values-rds.yaml` |
| Redis Sentinel | `redis-sentinel.yaml` |

## Export bundle

```bash
cd finance-governor
make fg-certification-external-full LEVEL=L5 PLATFORM=<your_org>
make fg-helm-enterprise > /tmp/fg-enterprise.yaml
curl -sf -H "x-internal-token: $TOKEN" $SIDECAR/internal/regulatory/export > regulatory-export.json
curl -sf -H "x-internal-token: $TOKEN" $SIDECAR/internal/decisions/verify-chain > chain-verify.json
```

Archive: attestation JSON, Helm render, export sample, chain verify output, partner checklist (signed).

## Related

- [institutional-gold-standard.md](institutional-gold-standard.md)
- [operations-runbook.md](operations-runbook.md)
