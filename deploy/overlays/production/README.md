# Production overlay

Institutional++ production topology:

- ExternalSecrets (Vault / AWS SM / GCP SM) — no plaintext credentials in Git
- Redis Sentinel HA (master + replica + 3 sentinels)
- Enterprise Istio overlay (egress allowlist + STRICT mTLS)
- Gateway live provider routing (`PROVIDER_MODE=live`)
- OIDC enabled on gateway + sidecar
- S3 Object Lock ledger anchor enabled

## Prerequisites

1. External Secrets Operator + `ClusterSecretStore` named `cluster-secret-store`
2. Populate secret manager keys listed in `externalsecret.yaml`
3. Istio control plane installed before sync
4. Provision S3 bucket: `deploy/infra/aws/ledger-anchor-bucket.yaml`

## Redis URL (in-cluster sentinel)

```
redis+sentinel://redis-sentinel:26379/mymaster/0
```

For managed memory (ElastiCache/MemoryDB), set `modelgovernor/redis-url` in your secret store instead.
