# Cybersecurity Governor — Plug and Play

**One-page path: demo → staging → production.** Pick your mode; run the commands.

| Mode | Audience | Time | Command |
|------|----------|------|---------|
| **A — Demo** | Prospects, SOC walkthrough | ~7 min | `make cg-stack-up && make cg-security-demo` |
| **B — Dev** | Engineers integrating APIs | ~5 min | `make cg-bootstrap && make cg-stack-up` |
| **C — Staging** | Customer VPC pilot | ~30 min | `make cg-prod-bootstrap && kubectl apply -k deploy/overlays/staging` |
| **D — Production** | Fortune-500 institutional++ | ~2 hr | `make cg-prod-bootstrap WITH_S3=1` + ESO + production overlay |

Full ModelGovernor family guide: [docs/plug-and-play.md](../docs/plug-and-play.md)

---

## Mode A — Sales demo (zero config)

**Requirements:** Docker + Compose + Make + curl

```bash
# From repository root
make demo-prereqs              # verify tools
make cg-security-demo          # auto-starts stack if needed, then Shadow Gap walkthrough
# or explicitly:
make cg-stack-up && make cg-security-demo
```

**Ports:** gateway `8100`, sidecar `8101`, identity `8103`, egress `8104`, witness `8105`, lineage `8106`, posture `8107`, content `8108`

`make cg-security-demo` **auto-starts** the stack if it is not already running (first build may take ~2 min).

If platforms fail to become healthy (common after a partial or stale run):

```bash
make cg-stack-reset    # docker compose down -v, rebuild, wait for all 6 platforms
make cg-security-demo
```

**Talk track:** [CYBER-SALES-DEMO.md](../CYBER-SALES-DEMO.md)

**Verify quality gate:**

```bash
make cg-spine-test             # 42+ unit tests
make cg-property-test          # Hypothesis hash-chain properties
```

---

## Mode B — Local dev (auto secrets)

Generates a `.env` with cryptographically random internal tokens (no more `change-me`).

```bash
cd cyber-governor
make cg-bootstrap              # writes .env from .env.example + random tokens
make cg-stack-up
make cg-spine-smoke
```

**Standalone platform (no spine):**

```bash
CG_SPINE_ENABLED=false uvicorn platforms.identity_gate.main:app --host 0.0.0.0 --port 8103
```

**Wire your SIEM/EDR (HTTP only):**

| Source | Endpoint |
|--------|----------|
| Okta / generic witness | `POST http://localhost:8105/ingest/generic` |
| CloudTrail | `POST http://localhost:8105/ingest/cloudtrail` |
| Falco | `POST http://localhost:8106/ingest/falco` |
| Tetragon | `POST http://localhost:8106/ingest/tetragon` |
| Governed commit | `POST http://localhost:8100/governed/commit` |

---

## Mode C — Staging (customer VPC)

**Requirements:** Kubernetes 1.28+, `kubectl`, External Secrets Operator (recommended)

### 1. Bootstrap secrets locally

```bash
cd cyber-governor
make cg-prod-bootstrap
# writes:
#   .env
#   deploy/generated/secrets.yaml        (apply once, gitignored)
#   deploy/generated/secret-manager-keys.json  (upload to your vault)
```

### 2. Load secrets into your vault

Upload keys from `deploy/generated/secret-manager-keys.json` to AWS Secrets Manager, GCP Secret Manager, or Vault — paths must match [deploy/overlays/staging/externalsecret.yaml](deploy/overlays/staging/externalsecret.yaml).

Minimum keys:

| Secret key | Purpose |
|------------|---------|
| `cybersecuritygovernor/database-url` | Sidecar + reconciler DSN |
| `cybersecuritygovernor/redis-url` | Diagnostic mode latch |
| `cybersecuritygovernor/cg-internal-tokens` | Spine ↔ platform auth |
| `cybersecuritygovernor/security-anchor-s3-bucket` | Witness quorum (optional in staging) |

### 3. Deploy

```bash
kubectl apply -k deploy/overlays/staging
kubectl -n cybersecuritygovernor wait --for=condition=complete job/cg-migration --timeout=300s
kubectl -n cybersecuritygovernor get pods
```

### 4. Smoke

```bash
kubectl -n cybersecuritygovernor port-forward svc/cg-gateway 8100:8100 &
curl -sf http://localhost:8100/healthz
```

---

## Mode D — Production institutional++

**Requirements:** Mode C + S3 Object Lock bucket + OIDC IdP + (recommended) Istio/mTLS

### 1. One-command bootstrap (secrets + optional S3)

```bash
cd cyber-governor
WITH_S3=1 BUCKET_NAME=your-corp-cg-security-anchor make cg-prod-bootstrap
```

This will:

- Generate production-grade random tokens and passwords
- Optionally provision the witness bucket via CloudFormation (`deploy/infra/aws/security-anchor-bucket.yaml`)
- Emit `deploy/generated/` manifests and a checklist

### 2. Populate secret manager (OIDC + HA)

Add to your vault (production overlay expects these):

| Key | Required |
|-----|----------|
| `cybersecuritygovernor/oidc-issuer-url` | Yes |
| `cybersecuritygovernor/oidc-audience` | Yes |
| `cybersecuritygovernor/database-url` | Yes (via PgBouncer in prod) |
| `cybersecuritygovernor/redis-url` | Yes (Sentinel or ElastiCache) |
| `cybersecuritygovernor/security-anchor-s3-bucket` | Yes |

### 3. Deploy production overlay

```bash
kubectl apply -k deploy/overlays/production
```

Production overlay enables:

- ExternalSecrets (replaces example secrets)
- 3× sidecar replicas, OIDC flags on config
- S3 Object Lock auto-enabled when bucket secret is present
- CronJobs: chain verify (15m), anchor head (hourly), synthetic probe, governance canary

### 4. Post-deploy verification

```bash
make cg-proof-test                    # full test pyramid (local)
# In cluster:
kubectl -n cybersecuritygovernor create job --from=cronjob/security-chain-verify manual-verify-$$
```

---

## Environment flip cheat sheet

| Variable | Demo | Staging | Production |
|----------|------|---------|------------|
| `CG_INTERNAL_TOKENS` | dev default | ESO / generated | ESO / rotated quarterly |
| `CG_SPINE_ENABLED` | `true` | `true` | `true` |
| `SECURITY_ANCHOR_S3_BUCKET` | unset | optional | **required** |
| `SECURITY_ANCHOR_S3_OBJECT_LOCK_ENABLED` | auto when bucket set | auto | `true` |
| `OIDC_ENABLED` | `false` | `false` | `true` |
| `REDIS_URL` | single instance | single | Sentinel / managed |

**Auto-config:** When `SECURITY_ANCHOR_S3_BUCKET` is set, Object Lock anchoring turns on automatically (no extra flag needed).

---

## Certification checklist

| Level | You are here when… |
|-------|-------------------|
| **L1** | `make cg-security-demo` passes |
| **L2** | `make cg-spine-test` + invariants green |
| **L3** | Postgres integration + invariant report PASS |
| **L4** | K8s deployed + S3 anchor + CronJobs green |

Details: [docs/cyber-governor/capability-matrix.md](../docs/cyber-governor/capability-matrix.md)

---

## Fortune-500: closing the “zero config” gap

Today you still wire **your** IdP, **your** secret store, and **your** data plane. We reduce that to **one bootstrap command + one kubectl apply**.

| Friction today | Improvement (shipped / path) |
|----------------|-------------------------------|
| Manual `change-me` tokens | `make cg-bootstrap` / `cg-prod-bootstrap` |
| Hand-written K8s secrets | `deploy/generated/secrets.yaml` + ExternalSecret overlays |
| S3 bucket setup | `WITH_S3=1 make cg-prod-bootstrap` (CloudFormation) |
| Object Lock flag forget | Auto-enable when bucket env is set |
| SIEM wiring | HTTP ingest URLs (table above) — no SDK |
| HA Postgres/Redis | Production overlay patches + [production-hardening.md](../docs/cyber-governor/production-hardening.md) |

**Next for true zero-config Fortune-500** (roadmap): Helm chart with cloud-specific subcharts (EKS/GKE/AKS), IRSA/workload identity for S3 without static keys, Crossplane bucket provisioning, and ArgoCD ApplicationSet. See [production-hardening.md](../docs/cyber-governor/production-hardening.md).

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `connection refused` on 8101 | `docker compose ps` — wait for `cg-postgres` healthy |
| `401` on `/internal/*` | Match `x-internal-token` to `CG_INTERNAL_TOKENS` in `.env` |
| Migration job failed | `kubectl logs -n cybersecuritygovernor job/cg-migration` |
| Chain verify FAIL | `GET /internal/security/verify-chain` on sidecar; check reconciler |
| S3 anchor skipped | Set `SECURITY_ANCHOR_S3_BUCKET`; sidecar needs AWS creds/IRSA |

---

## Quick reference

```bash
make cg-stack-up          # demo stack
make cg-bootstrap         # dev secrets
make cg-prod-bootstrap    # staging/prod secrets + optional S3
make cg-proof-test        # full quality gate
make cg-security-demo     # sales script
```

Docs: [reliability-testing.md](../docs/cyber-governor/reliability-testing.md) · [deploy/README.md](deploy/README.md) · [institutional-gold-standard.md](../docs/cyber-governor/institutional-gold-standard.md)
