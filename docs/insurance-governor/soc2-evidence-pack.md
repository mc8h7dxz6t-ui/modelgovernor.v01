# SOC 2 Type II Evidence Pack (Insurance Governor)

Map Insurance Governor artifacts to common SOC 2 Trust Services Criteria. Use with IG-ECP attestation reports in auditor data rooms.

## CC6 — Logical access

| Control | Evidence |
|---------|----------|
| OIDC gateway termination | `values-production.yaml` `config.oidcEnabled` |
| RBAC on sidecar admin routes | `routes_admin.py` `require_claims_admin` |
| Internal token segregation | `IG_INTERNAL_TOKEN` / ExternalSecrets |

**Proof:** `pytest insurance-governor/tests/test_auth_oidc.py` · Helm render with OIDC enabled

## CC7 — System operations

| Control | Evidence |
|---------|----------|
| Diagnostic mode (no poison pill) | `test_spine_lifecycle.py` |
| Invariant counters | `/metrics` · `PrometheusRule` |
| Chain verification CronJob | `claim-chain-verify` |

**Proof:** `make ig-certification-l4-ci` · `GET /internal/claims/verify-chain`

## CC8 — Change management

| Control | Evidence |
|---------|----------|
| GitOps manifests | `deploy/argocd/application-insurancegovernor-production-helm.yaml` |
| Helm versioned chart | `deploy/helm/insurancegovernor/Chart.yaml` |
| CI gates | `.github/workflows/ci.yml` `ig-certification-l4` |

**Proof:** ArgoCD Application manifest · CI green on merge

## CC9 — Risk mitigation

| Control | Evidence |
|---------|----------|
| Pre-execution crystallize | CCP on all platforms |
| Reserve caps + drift | `test_claim_gate_deep.py` |
| Chaos harness | `tests/chaos/test_toxiproxy_claim_ops.py` |

## A1 — Availability

| Control | Evidence |
|---------|----------|
| HPA, PDB, Istio | `values-enterprise.yaml` |
| PgBouncer + RDS overlay | `values-rds.yaml` |
| Redis Sentinel | `redis-sentinel.yaml` |

## Export bundle

```bash
make ig-certification-l4-ci
make ig-helm-enterprise > /tmp/ig-enterprise.yaml
curl -sf -H "x-internal-token: $TOKEN" $SIDECAR/internal/regulatory/export > regulatory-export.json
curl -sf -H "x-internal-token: $TOKEN" $SIDECAR/internal/claims/verify-chain > chain-verify.json
make ig-examiner-evidence
```

Archive: attestation JSON, Helm render, export sample, chain verify output, design partner package.

## Related

- [institutional-gold-standard.md](institutional-gold-standard.md)
- [operations-runbook.md](operations-runbook.md)
- [l4-certification.md](l4-certification.md)
