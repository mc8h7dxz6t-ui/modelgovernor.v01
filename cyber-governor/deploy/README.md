# Deploy kit

Production-grade Kubernetes manifests for Cybersecurity Governor.

## Apply

```bash
kubectl apply -k deploy/base/
```

## Ports (namespace `cybersecuritygovernor`)

| Service | Port |
|---------|------|
| cg-gateway | 8100 |
| cg-sidecar | 8101 |
| cg-reconciler | 8102 |

Platforms (IdentityGate, EgressLock, WitnessBridge, LineageIngest) deploy as separate workloads or Helm subcharts — see `docker-compose.yml` for reference images.

## Witness quorum (S3)

```bash
aws cloudformation deploy \
  --template-file deploy/infra/aws/security-anchor-bucket.yaml \
  --stack-name cybersecuritygovernor-security-anchor \
  --parameter-overrides BucketName=your-corp-security-anchor
```

Set `SECURITY_ANCHOR_S3_BUCKET` on cg-sidecar (separate AWS account recommended).

## CronJobs

| Job | Schedule | Endpoint |
|-----|----------|----------|
| `security-chain-verify` | every 15m | `GET /internal/security/verify-chain` |
| `security-chain-anchor` | hourly :15 | `POST /internal/security/anchor-head` |

## Strand egress circuit breaker

Apply label `cybersecuritygovernor.io/stranded=true` to pods when IdentityGate STRANDED — `strand-egress-deny-template` NetworkPolicy blocks egress except spine + DNS.
