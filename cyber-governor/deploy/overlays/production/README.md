# Production overlay — institutional++

## Prerequisites

1. `WITH_S3=1 BUCKET_NAME=... make cg-prod-bootstrap`
2. Upload all keys from `deploy/generated/secret-manager-keys.json` (including OIDC)
3. External Secrets Operator + ClusterSecretStore
4. (Recommended) IRSA for sidecar S3 writes — see `docs/cyber-governor/production-hardening.md`

## Apply

```bash
kubectl apply -k deploy/overlays/production
```

## What changes vs base

- Example Secret removed; ExternalSecret owns credentials
- 3× cg-sidecar replicas
- OIDC enabled on gateway
- S3 Object Lock anchoring enabled via ConfigMap

## Verify

```bash
kubectl -n cybersecuritygovernor get cronjobs
kubectl -n cybersecuritygovernor get externalsecret
```
