# Plug-and-play deployment modes

ModelGovernor ships three ready-to-run modes. Pick one per audience.

## Mode A — Sales demo (prospects, conferences, diligence calls)

**Requirements:** Docker only.

```bash
git clone <repo>
cd modelgovernor.v01
make demo-gold-up
make demo-gold
```

- Mock provider routing (no API keys)
- Full stack: gateway + sidecar + reconciler + Postgres + Redis
- All migrations applied automatically
- 3-minute scripted walkthrough with talk track

**Docs:** `docs/sales-demo.md`, `SALES-DEMO.md`

---

## Mode B — Staging / pilot (customer VPC)

**Requirements:** Kubernetes, External Secrets Operator, IdP (optional).

```bash
kubectl apply -k deploy/overlays/staging
# or
helm install modelgovernor deploy/helm/modelgovernor -f deploy/helm/modelgovernor/values-staging.yaml
```

- ExternalSecrets for credentials
- Single Redis (upgrade to Sentinel for prod)
- `PROVIDER_MODE=live` when API keys are ready

---

## Mode C — Production institutional++

**Requirements:** K8s, ESO, Istio (recommended), S3 Object Lock bucket.

```bash
# 1. Provision anchor bucket
aws cloudformation deploy \
  --template-file deploy/infra/aws/ledger-anchor-bucket.yaml \
  --stack-name modelgovernor-ledger-anchor \
  --parameter-overrides BucketName=your-corp-ledger-anchor

# 2. Populate secret manager (see deploy/overlays/production/externalsecret.yaml)

# 3. Deploy
kubectl apply -k deploy/overlays/production
# includes: Redis Sentinel, enterprise Istio, OIDC, live providers
```

**Or GitOps:**

```bash
kubectl apply -k deploy/argocd/
# ArgoCD syncs deploy/overlays/production
```

---

## Environment flip cheat sheet

| Variable | Demo | Production |
|---|---|---|
| `PROVIDER_MODE` | `mock` | `live` |
| `OIDC_ENABLED` | `false` | `true` |
| `GATEWAY_OIDC_ENABLED` | `false` | `true` |
| `REDIS_URL` | `redis://redis:6379/0` | `redis+sentinel://...` or ElastiCache |
| `LEDGER_ANCHOR_S3_*` | unset | bucket + Object Lock |

All production manifests are in-repo and CI-validated (`kustomize build`, `helm lint`).
