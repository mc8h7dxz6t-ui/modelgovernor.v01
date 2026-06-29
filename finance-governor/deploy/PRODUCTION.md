# Finance Governor — Production Deployment

Standalone from ModelGovernor. All paths under `finance-governor/`.

## Prerequisites

- Kubernetes 1.26+ (EKS/GKE/AKS)
- `helm` 3.x, `kubectl`
- OIDC IdP (Keycloak, Okta, Azure AD, Auth0)
- AWS account for S3 Object Lock anchor (recommended)

## 1. OIDC IdP

Create an OIDC client for Finance Governor:

| Setting | Value |
|---------|-------|
| Client ID / Audience | `finance-governor` |
| Grant types | Authorization Code (for humans); Client Credentials optional for automation |
| Roles / groups | `fg-commit`, `financial-admin`, `viewer` |

**Keycloak example issuer:**
```
OIDC_ISSUER_URL=https://keycloak.example.com/realms/finance-governor
OIDC_AUDIENCE=finance-governor
```

**Gateway** requires role `fg-commit` or `financial-admin` for `POST /governed/commit`.

**Sidecar** `/internal/*` requires `viewer`; `diagnostic/clear` and `decisions/anchor-head` require `financial-admin`.

Set `OIDC_ENABLED=true` and disable internal-token fallback in production:
```
OIDC_ALLOW_INTERNAL_TOKEN_FALLBACK=false
OIDC_INTERNAL_TOKEN_IS_ADMIN=false
```

## 2. S3 decision chain anchor

```bash
export DECISION_ANCHOR_S3_BUCKET=your-org-fg-decision-anchor-prod
export AWS_REGION=us-east-1
make fg-aws-anchor-bucket
```

Attach IAM policy from `deploy/infra/aws/irsa-sidecar-anchor-policy.json` (replace `BUCKET_NAME`) to an EKS IRSA role, then set in `values-production.yaml`:

```yaml
serviceAccount:
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::ACCOUNT_ID:role/fg-sidecar-decision-anchor
```

## 3. Generate secrets

```bash
cp .env.production.example .env.production
# Edit OIDC_ISSUER_URL, DECISION_ANCHOR_S3_BUCKET
make fg-prod-setup
```

This writes `.env.production` and applies Kubernetes secret `fg-internal`.

## 4. Helm install

```bash
# Optional: build and load images into cluster
export FG_BUILD_IMAGES=true

make fg-helm-install
```

Or manually:

```bash
./scripts/fg-helm-install.sh \
  --set oidc.issuerUrl=https://your-idp/realms/fg \
  --set oidc.audience=finance-governor \
  --set s3Anchor.bucket=your-bucket \
  --set s3Anchor.region=us-east-1 \
  --set s3Anchor.objectLock=true
```

## 5. Verify

```bash
kubectl -n finance-governor port-forward svc/fg-gateway 8090:8090 &
TOKEN=$(kubectl -n finance-governor get secret fg-internal -o jsonpath='{.data.fg-internal-tokens}' | base64 -d)

# Internal smoke (break-glass token)
curl -sf -H "x-internal-token: $TOKEN" http://localhost:8090/readyz

# OIDC governed commit
curl -sf -X POST http://localhost:8090/governed/commit \
  -H "Authorization: Bearer $OIDC_ACCESS_TOKEN" \
  -H 'content-type: application/json' \
  -d '{"platform":"wire_match","operation_id":"prod-1","facets":{"amount":"1.00"}}'

# Chain verify + anchor
curl -sf -H "x-internal-token: $TOKEN" http://localhost:8091/internal/decisions/verify-chain
curl -sf -X POST -H "x-internal-token: $TOKEN" http://localhost:8091/internal/decisions/anchor-head
```

## CronJobs (installed by Helm)

| Job | Schedule | Purpose |
|-----|----------|---------|
| `fg-decision-chain-verify` | hourly | Tamper check |
| `fg-decision-chain-anchor` | hourly :15 | DB + S3 anchor |
| `fg-governance-canary` | */10 min | readyz + diagnostic + verify |

## ExternalSecrets (enterprise)

Enable in `values-production.yaml`:

```yaml
externalSecrets:
  enabled: true
secrets:
  create: false
```

Store in AWS Secrets Manager:
- `fg/prod/internal-token`
- `fg/prod/postgres-password`
- `fg/prod/oidc-issuer-url`
- `fg/prod/oidc-audience`
- `fg/prod/decision-anchor-s3-bucket`
