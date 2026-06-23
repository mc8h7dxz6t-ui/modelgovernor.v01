# Platform B — Staging / Pilot

**SKU:** `MG-PLATFORM-STAGING`  
**Tagline:** Customer-VPC proof of value with live providers and GitOps-ready manifests.

---

## Executive summary

Kubernetes deployment for **60–90 day pilots** inside the buyer's VPC. Connects real OpenAI / Anthropic / Vertex keys via ExternalSecrets, validates governance semantics on production-shaped infra without full enterprise hardening (single Redis, optional OIDC).

| | |
|---|---|
| **Target buyer** | Platform engineering, FinOps, AI COE with K8s mandate |
| **Sales motion** | Paid POC after demo; success criteria → production contract |
| **Time to live** | 1–2 weeks (cluster + secrets + IdP optional) |
| **Suggested ACV (list)** | **$120K–$250K / year** (pilot) · **$40K–$80K** one-time implement |
| **Pre-revenue asset worth** | **$400K–$800K** |

---

## Full technical specification

### Topology

```
                    ┌─────────────────────────────────┐
  Ingress / LB      │  Gateway (1–2 replicas)         │
                    │  PROVIDER_MODE=live             │
                    └──────────────┬──────────────────┘
                                   │
                    ┌──────────────▼──────────────────┐
                    │  Sidecar (2–6 replicas, HPA)    │
                    │  Guardrails + circuit breaker   │
                    └──────────────┬──────────────────┘
           ┌───────────────────────┼───────────────────────┐
           ▼                       ▼                       ▼
      PgBouncer              Redis (single)          Reconciler (1–2)
           │                       │                       │
           ▼                       └───────────┬───────────┘
      PostgreSQL 16                            │
      append-only ledger ◄─────────────────────┘
```

### Deploy paths

```bash
# Kustomize
kubectl apply -k deploy/overlays/staging

# Helm
helm install modelgovernor deploy/helm/modelgovernor \
  -f deploy/helm/modelgovernor/values-staging.yaml
```

### Default scale (values-staging.yaml)

| Component | Replicas | Notes |
|---|---|---|
| Sidecar | 2 (HPA 2–6) | Policy + ledger API |
| Gateway | 1 | Governed dispatch edge |
| Reconciler | 1 | Expiry / stranded sweeps |
| Postgres | 1 (in-chart or managed) | Authoritative state |
| Redis | 1 | Guardrails + diagnostic pub/sub |
| Synthetic canary | CronJob */5 | Liveness probe |

### Configuration

| Variable | Pilot value | Production upgrade |
|---|---|---|
| `PROVIDER_MODE` | `live` | Same |
| `OIDC_ENABLED` | `false` → `true` | Platform C |
| `GATEWAY_OIDC_ENABLED` | `false` → `true` | Platform C |
| `REDIS_URL` | Single instance | Sentinel / ElastiCache |
| `LEDGER_ANCHOR_S3_*` | Disabled | Platform C |
| ExternalSecrets | Optional → recommended | Required in C |

### Provider routing (live)

| Provider | Model prefix | Secret key |
|---|---|---|
| OpenAI | `gpt-*`, `o*` | `OPENAI_API_KEY` |
| Anthropic | `anthropic/*` | `ANTHROPIC_API_KEY` |
| Vertex | `vertex/*` | GCP workload identity / SA JSON |

Implementation: `gateway/app/providers/` — router selects by model string.

### Core capabilities (all ✅ in pilot)

- Reserve-before-dispatch on every governed call
- `NUMERIC(24,12)` micro-cent pricing
- Per-trace atomic budget caps
- Drift enforcement + wallet lockout
- Append-only ledger + idempotent reserve/settle
- Redis guardrails with local fallback
- Provider circuit breaker with local fallback
- Diagnostic mode (write halt, read/admin live)
- Hash-chained ledger events
- Admin audit log on privileged actions
- Prometheus metrics + SLO counters
- Leader-elected reconciler sweeps

### Pilot success criteria (recommended SOW)

| Metric | Target |
|---|---|
| Reserve availability | ≥ 99.5% (30-day pilot window) |
| Reserve p95 latency | ≤ 500ms nominal load |
| Zero finance invariant violations | `finance_audit_violation_total` = 0 |
| Governed dispatch E2E | 100% of pilot workloads via gateway |
| Reconciler stranded holds | < 0.1% of reserves after 24h |

### Requirements

| Requirement | Notes |
|---|---|
| Kubernetes 1.26+ | EKS, GKE, AKS, on-prem |
| External Secrets Operator | Optional at pilot; templates in `deploy/overlays/staging` |
| Postgres 16 | In-cluster or RDS/Cloud SQL |
| Provider API keys | Via K8s Secret or ESO |
| IdP | Optional for pilot; required for production |

### Proof artifacts

```bash
pytest tests/integration/   # 57+ Tier-1 tests
make demo-gold              # narrative demo (parallel track)
kustomize build deploy/overlays/staging | kubectl apply --dry-run=client -f -
```

---

## Commercial packaging

### Suggested pilot SOW (12 weeks)

| Phase | Weeks | Deliverable |
|---|---|---|
| Deploy | 1–2 | Staging overlay in buyer VPC |
| Integrate | 3–6 | 1–3 apps on `POST /governed/dispatch` |
| Observe | 7–10 | SLO dashboard, drift drills |
| Decision | 11–12 | Production proposal (Platform C) |

### Pricing guidance (pre-revenue list)

| Line item | Range |
|---|---|
| Annual platform license (pilot tier) | $120K–$250K |
| Implementation / PS | $40K–$80K one-time |
| Support (business hours) | 15–20% of license |

### What's not included (upsell to C or D)

- Redis Sentinel HA
- S3 Object Lock external anchor
- Istio STRICT mTLS + egress allowlist
- 24×7 SRE / dedicated TAM

---

## Pre-revenue worth

| Component | Estimate |
|---|---|
| Staging Kustomize + Helm values | $80K–$140K |
| Live provider router (3 providers) | $120K–$200K |
| ESO integration templates | $40K–$70K |
| Pilot runbooks + test coverage | $80K–$150K |
| **Total asset worth** | **$400K–$800K** |

---

## Upgrade path

→ **Platform C** — add Sentinel, OIDC, S3 anchor, 2+ reconciler, enterprise overlay  
→ **Platform D** — Istio egress + mTLS if InfoSec gate

See [03-production-institutional.md](03-production-institutional.md).
