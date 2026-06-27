# Staging overlay

Uses External Secrets Operator instead of `secrets.example.yaml`.

## Prerequisites

1. `make cg-prod-bootstrap` — generates `deploy/generated/secret-manager-keys.json`
2. Upload keys to your secret manager (paths must match `externalsecret.yaml`)
3. ClusterSecretStore `cluster-secret-store` configured

## Apply

```bash
kubectl apply -k deploy/overlays/staging
kubectl -n cybersecuritygovernor wait --for=condition=complete job/cg-migration --timeout=300s
```

Removes the example Secret from base and pulls credentials from ESO.
