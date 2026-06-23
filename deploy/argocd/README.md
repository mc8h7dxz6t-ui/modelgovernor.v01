# ArgoCD manifests for ModelGovernor GitOps

See [docs/gitops.md](../../docs/gitops.md) for full bootstrap instructions.

## Files

| File | Purpose |
|---|---|
| `appproject.yaml` | Argo CD AppProject with `modelgovernor` namespace destination |
| `application-staging.yaml` | Kustomize → `deploy/overlays/staging` |
| `application-production.yaml` | Kustomize → `deploy/overlays/production` |
| `application-production-helm.yaml` | Helm chart + `values-production.yaml` |
| `application-gitops.yaml` | App-of-apps bootstrap (apply once manually) |

## Quick apply

```bash
kubectl apply -f deploy/argocd/appproject.yaml
kubectl apply -f deploy/argocd/application-production.yaml
```

Update `spec.source.repoURL` and `targetRevision` in each Application to match your fork/branch.
