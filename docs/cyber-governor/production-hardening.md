# Fortune-500 production hardening — Cybersecurity Governor

How to move from **“bootstrap + kubectl”** to **near-zero-config enterprise** deploy.

## Current state (L4 Gold — shipped)

You can reach institutional++ production today with:

```bash
make cg-stack-up
WITH_S3=1 BUCKET_NAME=corp-cg-anchors make cg-prod-bootstrap
# upload deploy/generated/secret-manager-keys.json to your vault
kubectl apply -k deploy/overlays/production
```

What still requires **your** environment (not genericizable):

1. **Identity** — OIDC issuer + audience (every corp has a different IdP)
2. **Data plane** — managed Postgres, Redis, networking (VPC-specific)
3. **Secret store** — AWS SM / GCP SM / Vault (account boundaries)

What we **already** automated:

| Step | Automation |
|------|------------|
| Internal spine tokens | `scripts/bootstrap-secrets.sh` — `openssl rand -hex 32` |
| K8s Secret manifest | `deploy/generated/secrets.yaml` |
| Vault key manifest | `deploy/generated/secret-manager-keys.json` |
| S3 witness bucket | `WITH_S3=1` → CloudFormation `security-anchor-bucket.yaml` |
| Object Lock enable | Settings auto-enable when `SECURITY_ANCHOR_S3_BUCKET` is set |
| Migrations | `migration-job.yaml` on deploy |
| Chain verify + anchor | CronJobs in base manifest |
| Strand egress | NetworkPolicy template (label `cybersecuritygovernor.io/stranded=true`) |

---

## Tier 1 — Day 1 (minimal ops burden)

**Goal:** No dev tokens in any environment.

| Action | Command / artifact |
|--------|-------------------|
| Rotate all spine tokens | `make cg-prod-bootstrap` (re-run, push new keys to vault) |
| ESO instead of static Secret | `deploy/overlays/production/externalsecret.yaml` |
| IRSA for S3 (no static AWS keys) | Annotate sidecar SA: `eks.amazonaws.com/role-arn` (see below) |
| Ingress TLS | cert-manager + your ingress controller |

### EKS IRSA example (S3 anchor without access keys)

```yaml
# deploy/overlays/production/sidecar-sa-irsa.yaml (patch)
apiVersion: v1
kind: ServiceAccount
metadata:
  name: cg-sidecar
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::ACCOUNT:role/cybersecuritygovernor-anchor-writer
```

IAM policy: `s3:PutObject`, `s3:GetObject` on anchor bucket prefix only.

---

## Tier 2 — Week 1 (HA data plane)

**Goal:** Survive AZ failure and connection storms.

| Component | Recommendation |
|-----------|----------------|
| Postgres | RDS Multi-AZ or Cloud SQL HA; point `database-url` at PgBouncer |
| PgBouncer | Pool size 3–5 per sidecar pod; `pool_mode=transaction` |
| Redis | ElastiCache / Memorystore with replica; or Redis Sentinel overlay |
| Sidecar | 3+ replicas (production overlay sets this) |
| Reconciler | 1 leader (built-in); 2 replicas for fast failover |

PgBouncer DSN pattern:

```
postgresql+psycopg://cg_app:***@pgbouncer.cybersecuritygovernor.svc:6432/cybersecuritygovernor
```

---

## Tier 3 — Month 1 (security + compliance)

**Goal:** Pass enterprise security review without custom engineering.

| Control | Mechanism |
|---------|-----------|
| **Authentication** | OIDC on gateway + `/internal/*` (set `OIDC_ENABLED=true`) |
| **Encryption in transit** | Istio STRICT mTLS or service mesh equivalent |
| **Encryption at rest** | RDS encryption, S3 KMS (template uses SSE-KMS) |
| **Audit proof** | Hourly `security-chain-anchor` CronJob → S3 Object Lock |
| **Tamper detection** | 15m `security-chain-verify` + PrometheusRule alerts |
| **Blast radius** | NetworkPolicy: sidecar ingress only from gateway + platforms |
| **STRAND circuit breaker** | `strand-egress-deny-template` NetworkPolicy |

### OIDC minimum config

```yaml
# ConfigMap patch (production overlay)
OIDC_ENABLED: "true"
GATEWAY_OIDC_ENABLED: "true"
```

Secrets (via ESO):

- `cybersecuritygovernor/oidc-issuer-url`
- `cybersecuritygovernor/oidc-audience`

---

## Tier 4 — True zero-config (roadmap)

These are the remaining steps to **Fortune-500 flip-switch** deploy:

### 4a. Helm chart with cloud presets

```bash
helm install cg oci://your-registry/cybersecuritygovernor \
  --set cloud.provider=aws \
  --set cloud.region=us-east-1 \
  --set witnessAnchor.autoProvision=true
```

Subcharts would provision: RDS, ElastiCache, S3 bucket, IRSA role, ESO SecretStore — **one values file per cloud**.

### 4b. GitOps ApplicationSet

```yaml
# ArgoCD: one Application per cluster from cluster generator
# Sync: deploy/overlays/production + cluster-specific values
```

### 4c. Crossplane / ACK resource claims

```yaml
apiVersion: s3.aws.crossplane.io/v1beta1
kind: Bucket
metadata:
  name: cg-security-anchor
spec:
  forProvider:
    objectLockEnabled: true
```

Bucket name flows to ExternalSecret via Crossplane composition — **no human S3 console step**.

### 4d. Auto-discovery wiring

| Signal | Auto-action |
|--------|-------------|
| `AWS_REGION` + IRSA role present | Enable S3 anchor, set region |
| `KUBERNETES_SERVICE_HOST` | Use in-cluster Redis/Postgres service DNS |
| ESO `ClusterSecretStore` exists | Skip static `secrets.yaml`, use ExternalSecret only |
| Falco sidecar detected | Pre-register LineageIngest webhook URL in ConfigMap |

### 4e. Operator pattern (long-term)

A `CyberGovernor` CRD:

```yaml
apiVersion: security.governor.io/v1
kind: CyberGovernor
metadata:
  name: prod
spec:
  tier: institutional-plus-plus
  witnessAnchor:
    provider: aws
    retentionYears: 10
  oidc:
    issuerURL: https://login.corp.example
```

Operator reconciles Deployments, CronJobs, ExternalSecrets, S3 bucket.

---

## Comparison: config burden

| Stage | Human steps | Time |
|-------|-------------|------|
| **Demo** | 1 (`make cg-stack-up`) | 5 min |
| **Dev** | 2 (`cg-bootstrap` + stack up) | 10 min |
| **Staging** | 4 (bootstrap, vault upload, kubectl, smoke) | 30–60 min |
| **Production (today)** | 6 (+ OIDC, HA DB, IRSA, monitoring) | 2–4 hr |
| **Production (roadmap)** | 1 (Helm preset or CRD) | 15 min |

---

## What to do now

1. Run `make cg-prod-bootstrap` in your staging cluster context
2. Apply `deploy/overlays/staging` and validate CronJobs
3. Promote to `deploy/overlays/production` with OIDC + IRSA
4. Track Helm/operator work as Phase 4 in your internal backlog

Related: [operations-runbook.md](../cybersecurity-governor/operations-runbook.md) · [capability-matrix.md](../cybersecurity-governor/capability-matrix.md) · [slo-definitions.md](slo-definitions.md)
