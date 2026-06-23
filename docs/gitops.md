# GitOps — ArgoCD & Helm

Deploy the full ModelGovernor production topology (Postgres, PgBouncer, Redis, sidecar,
gateway, reconciler, OTEL, monitoring, synthetic canary) via **GitOps**.

Two supported paths:

| Method | Path | Best for |
|---|---|---|
| **Kustomize + ArgoCD** | `deploy/overlays/{staging,production}` | Matches CI kustomize validation |
| **Helm + ArgoCD** | `deploy/helm/modelgovernor` | Value-driven multi-cluster rollouts |

---

## Prerequisites

- Kubernetes 1.25+
- [Argo CD](https://argo-cd.readthedocs.io/) 2.9+ in `argocd` namespace
- Prometheus Operator CRDs (for `PodMonitor` / `PrometheusRule`)
- External Secrets Operator (optional, recommended for production)
- Container images published: `modelgovernor/sidecar`, `modelgovernor/reconciler`, `modelgovernor/gateway`

---

## Bootstrap (one-time)

### 1. Create the AppProject and register Applications

```bash
# Edit repoURL in deploy/argocd/*.yaml if using a fork
kubectl apply -f deploy/argocd/appproject.yaml
kubectl apply -f deploy/argocd/application-staging.yaml
kubectl apply -f deploy/argocd/application-production.yaml
# Optional Helm-based production app (do not run both kustomize + helm to same namespace):
# kubectl apply -f deploy/argocd/application-production-helm.yaml
```

Or bootstrap the app-of-apps (applies all apps except the bootstrap file itself):

```bash
kubectl apply -f deploy/argocd/application-gitops.yaml
```

### 2. Provision secrets before first sync

Production should use External Secrets (`deploy/base/externalsecret.example.yaml` or Helm
`externalSecrets.enabled: true`).

Minimum secret keys in `modelgovernor-secrets`:

- `database-url` — via PgBouncer (`pgbouncer:6432`)
- `database-url-direct` — direct Postgres (`postgres:5432`) for migrations
- `redis-url`
- `sidecar-internal-tokens`
- `postgres-password`

---

## ArgoCD Applications

| Application | Source | Destination |
|---|---|---|
| `modelgovernor-staging` | `deploy/overlays/staging` (kustomize) | `modelgovernor` |
| `modelgovernor-production` | `deploy/overlays/production` (kustomize) | `modelgovernor` |
| `modelgovernor-production-helm` | `deploy/helm/modelgovernor` + `values-production.yaml` | `modelgovernor` |

Production kustomize Application enables automated sync with prune/self-heal and ignores
HPA-driven replica drift on sidecar.

### Sync ordering

| Wave | Resources |
|---|---|
| 0 | Namespace, secrets (ExternalSecret) |
| 1 | Postgres, Redis, configmaps, migration SQL bundle |
| 2 | PgBouncer, migration PreSync Job |
| 3 | Sidecar, gateway, reconciler, OTEL, network policies |
| 4 | PodMonitors, PrometheusRules, Grafana dashboard, synthetic canary |

Migration job uses ArgoCD `PreSync` hook (`deploy/base/migration-job.yaml`).

---

## Helm (standalone or via ArgoCD)

```bash
# Render
helm template modelgovernor deploy/helm/modelgovernor \
  -f deploy/helm/modelgovernor/values-production.yaml \
  --namespace modelgovernor

# Install (dev — creates inline secrets)
helm upgrade --install modelgovernor deploy/helm/modelgovernor \
  -f deploy/helm/modelgovernor/values-staging.yaml \
  --namespace modelgovernor --create-namespace \
  --set secrets.create=true \
  --set secrets.postgresPassword=devpass \
  --set secrets.sidecarInternalTokens=dev-token
```

### Key values

| Value | Description |
|---|---|
| `sidecar.replicas` / `sidecar.hpa.*` | Sidecar scale |
| `gateway.enabled` | Governance gateway deployment |
| `externalSecrets.enabled` | Wire ExternalSecret instead of inline Secret |
| `postgres.enabled` | In-cluster Postgres (disable when using RDS/Cloud SQL) |
| `migrations.argocd.preSyncHook` | ArgoCD PreSync migration job |

---

## Topology managed

```
Namespace: modelgovernor
├── postgres / pgbouncer / redis
├── sidecar (+ HPA, PDB, PodMonitor)
├── gateway
├── reconciler (+ PodMonitor, leader election)
├── otel-collector
├── migration Job (PreSync)
├── NetworkPolicy
├── PrometheusRule + Grafana dashboard ConfigMap
└── synthetic-canary CronJob
```

---

## CI validation

`.github/workflows/ci.yml` runs `kustomize build` on overlays and `helm template` on the
chart. Migrations are committed under `deploy/base/migrations/` and
`deploy/helm/modelgovernor/files/migrations/` for GitOps reproducibility.

---

## Related docs

- `docs/ha-strategy.md` — HA and scaling
- `docs/observability.md` — metrics, SLOs, dashboards
- `docs/gateway-integration.md` — governed dispatch API
