# Finance Governor L4 Gold Certification

**L4 Gold** = L3 Institutional++ plus enterprise K8s HA, full platform fleet, and GitOps deploy.

## Requirements checklist

| Requirement | Artifact | Verify |
|-------------|----------|--------|
| Tier 4 Toxiproxy chaos | `tests/chaos/test_toxiproxy_fg_spine.py` | `make fg-chaos-test` |
| Hash chain + S3 anchor | sidecar anchor CronJob | `make fg-demo-gold` step 5 |
| OIDC + RBAC | `values-production.yaml` | `oidc.enabled: true` |
| PgBouncer pooling | `templates/pgbouncer.yaml` | `helm template -f values-enterprise.yaml` |
| Redis Sentinel HA | `templates/redis-sentinel.yaml` | enterprise render includes sentinel |
| HPA (3–12 sidecar) | `templates/hpa.yaml` | enterprise render |
| PDB anti-affinity | `templates/pdb.yaml` + `fg.podAntiAffinity` | enterprise render |
| All 5 platforms in K8s | `templates/platforms.yaml` | `fg-platform-canary` CronJob |
| Prometheus PodMonitor + SLO rules | `podmonitor.yaml`, `prometheus-rules.yaml` | enterprise render |
| Istio STRICT mTLS overlay | `kustomize/overlays/enterprise/` | `kustomize build` |
| ArgoCD GitOps | `deploy/argocd/application-production.yaml` | `kubectl apply -f deploy/argocd/` |
| 80+ tests | `tests/` | `make fg-certification-l4` |

## Install (L4 Gold)

```bash
# 1. Helm — production + enterprise overlays
helm upgrade --install fg ./deploy/helm/finance-governor \
  -f ./deploy/helm/finance-governor/values-production.yaml \
  -f ./deploy/helm/finance-governor/values-enterprise.yaml \
  --namespace finance-governor --create-namespace

# 2. Istio enterprise mesh (optional, requires Istio in cluster)
kustomize build ./deploy/kustomize/overlays/enterprise | kubectl apply -f -

# 3. GitOps (ArgoCD)
kubectl apply -f ./deploy/argocd/
```

## Certification commands

```bash
make fg-certification-l4    # full L4 gate: unit + postgres + chaos + helm enterprise
make fg-helm-enterprise     # render L4 manifest smoke
make fg-chaos-test          # Tier 4 toxiproxy
make fg-demo-gold           # 15-step walkthrough
make fg-demo-gold-reliability
```

## HA topology (L4)

| Component | L4 minimum |
|-----------|------------|
| Sidecar | 5 replicas, HPA 3–12, PDB minAvailable 3 |
| Gateway | 3 replicas, HPA 2–8 |
| Reconciler | 3 replicas, leader election |
| PgBouncer | 3 replicas, transaction pooling |
| Redis | Sentinel 3 + master + replica |
| Platforms | 2 replicas each, Postgres-backed audit |

## Related

- [external-certification.md](external-certification.md) — FG-ECP vendor attestation (L5)
- [institutional-gold-standard.md](../../docs/finance-governor/institutional-gold-standard.md)
- [operations-runbook.md](../../docs/finance-governor/operations-runbook.md)
- [PRODUCTION.md](../deploy/PRODUCTION.md)
