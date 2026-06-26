# Platform model — standalone or spine

Each Cybersecurity Governor platform is a **clean, deployable service** — not a feature flag in a monolith.

## Deployment modes

### Mode A — Standalone (default for eval)

```bash
CG_SPINE_ENABLED=false
```

- Platform uses `platforms/common/threat_crystal.py` locally
- No Postgres / Redis required
- Same TCP envelope semantics
- Ideal for: IdP webhook sidecar, egress proxy POC, witness ingest only

### Mode B — Spine-connected (institutional++)

```bash
CG_SPINE_ENABLED=true
CG_SIDECAR_URL=http://cg-sidecar:8101
```

- All crystals persisted to Postgres with hash chain
- Threat Mesh enforced across platforms
- Reconciler strands expired critical sessions
- Forensic reconstruct API available

## Platform summary

| Platform | Port | Entry API | Integrates with |
|----------|------|-----------|-----------------|
| IdentityGate | 8103 | `POST /session/arm` | Okta, Azure AD, custom IdP (via adapter) |
| EgressLock | 8104 | `POST /egress/evaluate` | S3 proxy, API gateway, DLP |
| WitnessBridge | 8105 | `POST /ingest/{source}` | Okta, CloudTrail, Splunk HEC-style generic |
| LineageIngest | 8106 | `POST /ingest/falco` etc. | Falco, Tetragon, generic |
| PostureReconcile | 8107 | `POST /posture/evaluate` | Wiz, Prisma, K8s admission webhooks |
| ContentGuard | 8108 | `POST /content/evaluate` | CMS, email gateway, internal APIs |

## Docker Compose profiles

```bash
# Spine only
docker compose up -d cg-postgres cg-redis cg-sidecar cg-reconciler cg-gateway

# Spine + one platform
docker compose up -d cg-sidecar cg-identity-gate

# Full stack
make cg-stack-up
```

## Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `CG_SPINE_ENABLED` | `false` | Use spine sidecar vs local crystals |
| `CG_SIDECAR_URL` | `http://localhost:8101` | Spine sidecar base URL |
| `CG_INTERNAL_TOKEN` | — | Internal auth for spine APIs |
