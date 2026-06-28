# Platform C — Production Institutional++

**SKU:** `MG-PLATFORM-PRODUCTION`  
**Tagline:** Regulated-enterprise AI spend control plane — ledger-backed, tamper-evident, GitOps-native.

---

## Executive summary

Full production topology for organizations that cannot tolerate post-hoc AI budget surprises, ledger gaps, or poison-pill outages. Bundles Redis Sentinel HA, dual OIDC termination (gateway + sidecar), S3 Object Lock ledger anchoring, hourly chain verification CronJobs, and optional Istio enterprise overlay.

| | |
|---|---|
| **Target buyer** | Regulated finance, Fortune 500 platform teams, AI-heavy enterprises ($5M+ annual LLM spend) |
| **Sales motion** | Pilot success → multi-year enterprise agreement |
| **Time to live** | 4–8 weeks (with managed Postgres, Istio, IdP) |
| **Maturity tier** | **L5** — `make plug` + production Helm overlays |

---

## Full technical specification

### Production topology

```
┌──────────────────────────────────────────────────────────────────┐
│  Istio mesh (optional Platform D) — STRICT mTLS, egress allow   │
└────────────────────────────┬─────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────┐
│  Gateway ×2  │  OIDC @ edge  │  PROVIDER_MODE=live               │
└────────────────────────────┬─────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────┐
│  Sidecar ×3–12 (HPA)  │  OIDC RBAC  │  Guardrails + CB fallback │
└───────┬────────────────────────────────────────────┬─────────────┘
        │                                            │
        ▼                                            ▼
   PgBouncer ×3                              Redis Sentinel
        │                                    (master+replica+3 sentinels)
        ▼                                            │
   PostgreSQL 16 ◄───────────────────────────────────┘
   • wallets, operations, ledger_events
   • hash chain (migration 0009)
   • admin_audit (0010)
   • ledger_chain_anchors (0011)
        ▲
        │
   Reconciler ×2 (advisory lock leader election)
```

### Deploy

```bash
# 1. S3 anchor bucket (Object Lock)
aws cloudformation deploy \
  --template-file deploy/infra/aws/ledger-anchor-bucket.yaml \
  --stack-name modelgovernor-ledger-anchor

# 2. Populate secret manager (see externalsecret.yaml)

# 3. Apply production overlay
kubectl apply -k deploy/overlays/production

# GitOps alternative
kubectl apply -k deploy/argocd/
```

### Default scale (values-production.yaml)

| Component | Replicas | HA notes |
|---|---|---|
| Sidecar | 3 (HPA 3–12) | PDB, anti-affinity |
| Gateway | 2 | OIDC termination |
| Reconciler | 2 | Single leader via PG advisory lock |
| PgBouncer | 3 | Connection pooling |
| Redis Sentinel | 1 master + 1 replica + 3 sentinels | In-overlay or ElastiCache |
| Postgres | Managed recommended | RDS / Cloud SQL / Aurora |

### Security & compliance surfaces

| Control | Implementation |
|---|---|
| Authentication | Gateway OIDC + Sidecar OIDC (`auth_oidc.py`) |
| RBAC | Viewer / Financial Admin roles on `/internal/*` |
| Secrets | ExternalSecrets — Vault, AWS SM, GCP SM |
| Audit | `admin_audit` table + hash-chained `ledger_events` |
| Tamper evidence | Hourly `ledger-chain-verify` CronJob |
| External anchor | Hourly `ledger-chain-anchor` → S3 Object Lock |
| Network | Istio egress allowlist (Platform D) |
| Egress domains | `api.openai.com`, `api.anthropic.com` (+ Vertex via GCP SA) |

### SLO commitments (institutional++)

| SLO | Target | Alert |
|---|---|---|
| Reserve availability | **99.5%** / 30d | `ModelGovernorReserveAvailabilitySLO` |
| Reserve p95 latency | **≤ 500ms** | `ModelGovernorReserveLatencySLO` |
| Finance invariants | **Zero budget** | Immediate critical on any counter |

Finance invariants (no error budget): negative wallet, duplicate refund/settlement, post-sweep audit failure.

### CronJob operational probes

| Job | Schedule | Purpose |
|---|---|---|
| `synthetic-canary` | */5 | Gateway / sidecar / reconciler liveness |
| `governance-canary` | */10 | Diagnostic + verify-chain smoke |
| `ledger-chain-verify` | hourly | Hash-chain integrity (422 on break) |
| `ledger-chain-anchor` | hourly :15 | S3 anchor of verified head |

### Data model highlights

| Migration | Capability |
|---|---|
| 0008 | `NUMERIC(24,12)` micro-token amounts |
| 0009 | Ledger event hash chain + seals |
| 0010 | Privileged admin audit log |
| 0011 | External anchor metadata |

### Observability

| Surface | Auth | Content |
|---|---|---|
| `/metrics/prometheus` | None | RED metrics, process stats |
| `/metrics` | Internal token | DB aggregates, invariant counters |
| PrometheusRule | N/A | SLO burn-rate alerts in `deploy/base/` |
| OTEL | Optional | Collector template in Helm chart |

### Reliability mechanisms

| Failure | Automated response |
|---|---|
| Redis outage | Local guardrail + circuit breaker fallback per pod |
| Finance invariant break | Diagnostic mode — writes 503, reads/admin live |
| Ledger tamper | Chain verify fails → alert / CronJob failure |
| Provider storm | Circuit open → reserve blocked per provider |
| Reconciler partition | Standby idle; leader holds advisory lock |

### CI / quality gate

| Tier | Scope |
|---|---|
| Tier 1 | 57+ SQLite integration tests (< 2 min) |
| Tier 2 | Postgres vigorous semantics |
| Tier 3 | Load harness + invariant JSON reports |
| Tier 4 | Toxiproxy chaos (finance ops finals) |

### Requirements

| Requirement | Notes |
|---|---|
| Kubernetes 1.26+ | Production-grade cluster |
| External Secrets Operator | **Required** |
| Istio | Recommended (Platform D overlay) |
| Managed Postgres 16 | **Required** for production |
| S3 Object Lock bucket | **Required** for anchor |
| Corporate IdP | Okta / Keycloak / Entra — **Required** |
| Redis Sentinel or ElastiCache | **Required** |

---

## Deployment tiers (technical)

| Tier | Includes |
|---|---|
| **Standard** | Platform C, business-hours support path, quarterly review hooks |
| **Premium** | + Platform D, extended support SLO templates |
| **Strategic** | + custom SLOs, on-site runbooks, chaos test attestation |

### Professional services scope (typical SOW items)

| Service | Scope |
|---|---|
| Production implementation | Helm + Kustomize rollout |
| IdP + OIDC integration | Gateway + sidecar JWT validation |
| Istio / zero-trust rollout | Platform D overlay (or bundled) |
| Annual health check / chaos day | Toxiproxy + load tier attestation |

### ROI narrative (for CFO)

| Risk without MG | Cost driver |
|---|---|
| Runaway agent loops | Material incident tail risk |
| Unreconciled provider bills | 5–15% LLM overspend |
| Audit failure on AI spend | Regulatory / SOX exposure |
| Homegrown rebuild | 12–18 month engineering cycle |

---

## Maturity proof

| Component | Verified by |
|---|---|
| Production overlay + Sentinel manifests | `deploy/overlays/production/` |
| Ledger hash-chain + S3 anchor system | `verify-chain` + anchor CronJob |
| OIDC gateway + sidecar RBAC | JWKS live tests in L4 CI |
| CronJobs, SLO rules, reconciler HA | Helm templates + chaos tier |
| ExternalSecrets + GitOps (ArgoCD, Helm) | Staging → prod promotion path |
| Test suite + chaos / load tiers | `make mg-certification-l4-ci` |

---

## Add-ons

→ **Platform D — Enterprise Security Pack** — Istio mTLS, egress allowlist  
→ **Managed control plane** (future SaaS) — separate operating model

See [04-enterprise-security-pack.md](04-enterprise-security-pack.md).
