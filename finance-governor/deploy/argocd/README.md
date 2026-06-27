# ArgoCD GitOps — Finance Governor L4 Gold

```bash
kubectl apply -f finance-governor/deploy/argocd/
```

Deploys `finance-governor-production` Application with:
- `values-production.yaml` — OIDC, S3 anchor, ExternalSecrets
- `values-enterprise.yaml` — PgBouncer, Redis Sentinel, HPA, platforms, Istio-ready network policy

Enterprise Istio overlay (separate apply):

```bash
kustomize build finance-governor/deploy/kustomize/overlays/enterprise | kubectl apply -f -
```
