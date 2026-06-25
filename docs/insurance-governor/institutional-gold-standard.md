# Institutional++ Gold Standard — Insurance Governor

## Certification levels

| Level | Status | Requirements |
|-------|--------|--------------|
| **L1 Platform** | Done | Standalone ClaimGate, SpineAdapter local mode |
| **L2 Institutional** | Done | Diagnostic mode, claim_ops probes, CCP |
| **L3 Institutional++** | Done | Hash chain verify, anchor table, guardrails + fallback |
| **L4 Gold** | Done | 4-tier CI, Helm chart, load harness, Prometheus rules |

## L4 Gold checklist (implemented)

### Data plane
- [x] Append-only `claim_events` with hash chain on all paths (including sweeps)
- [x] `claim_ops.assert_claim_ops_invariants()` — 7 probes
- [x] Thread-safe `append_claim_event` for concurrent sealing
- [x] `GET /internal/claims/verify-chain`
- [x] `POST /internal/claims/anchor-head` + `claim_chain_anchors` migration

### Degradation
- [x] Redis guardrails + symmetric local fallback (`guardrails.py`, `fallback_limiter.py`)
- [x] Reconciler halts sweeps in diagnostic mode
- [x] Diagnostic write halt on crystallize/commit

### Security
- [x] OIDC JWT + RBAC scaffold (`auth_oidc.py`)
- [x] Admin audit log on privileged actions (`admin_audit.py`)
- [x] Claims-admin gate on diagnostic clear and anchor

### Observability
- [x] `/metrics/prometheus` RED metrics
- [x] Prometheus P1 rules in `deploy/helm/insurancegovernor/files/prometheus-rules.yaml`
- [x] Governance canary (Helm) hits `/internal/claims/verify-chain`

### Testing pyramid
- [x] Tier 1: `make ig-spine-test` (14 tests)
- [x] Tier 2: `test_postgres_vigorous.py` (CI `ig-test-tier2`)
- [x] Tier 3: `tests/load/test_ig_load_harness.py` (CI `ig-test-tier3`)
- [x] Tier 4: Toxiproxy chaos (`docker-compose.chaos.yml`, `tests/chaos/test_toxiproxy_claim_ops.py`, CI `ig-test-tier4-chaos`)

### Deploy
- [x] `deploy/helm/insurancegovernor/` — forked from ModelGovernor with IG ports/migrations
- [x] CI: `ig-test-tier1` through `ig-test-tier4-chaos`, `ig-validate-helm`, `ig-build-images`

## Certification commands

```bash
make ig-spine-test        # Tier 1
make ig-load-test         # Tier 3
make ig-certification     # Tier 1 + load + artifact report
make ig-chaos-test        # Tier 4 (requires chaos compose up)
helm lint deploy/helm/insurancegovernor
```

## Remaining for production hardening (post-L4)
- S3 Object Lock anchor in production overlay (config present, enable per env)
- PgBouncer + Redis Sentinel HA rehearsal compose for IG
- ArgoCD Application manifest for `insurancegovernor` namespace
