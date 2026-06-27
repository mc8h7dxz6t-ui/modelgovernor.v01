# Cybersecurity Governor — Sales Demo

**Plug-and-play institutional++ security walkthrough. No API keys. No cloud. ~7 minutes.**

Closes **The Shadow Gap** live: identity violation → mesh block → blocked egress — with Threat Crystal Protocol, Security Enforcement Mesh, and hash-chain verification.

## Prerequisites

```bash
make demo-prereqs-install   # Docker + Compose + curl + make (once)
```

## Run

```bash
make cg-stack-up && make cg-demo
# spine smoke + EgressGovern allowlist demo (ports 8120–8123)
```

Or tests-only:

```bash
make cg-spine-test          # unit + property tests
make cg-certification-l4-ci # L4 Gold CI gate
```

**Production path:** Helm chart at `deploy/helm/cybersecuritygovernor/` — see [docs/cybersecurity-governor/operations-runbook.md](docs/cybersecurity-governor/operations-runbook.md)

## Talk track (7 minutes)

### 1. The problem (30s)

Multi-vector attacks exploit three gaps incumbents cannot close:

- **Time-skew** — logs arrive out of true order
- **Ephemeral erasure** — serverless assets vanish before IR
- **Log mutation** — admins delete audit trails

SIEM correlates guesses. **Cybersecurity Governor binds authorization to Threat Crystals.**

### 2. Governed egress (90s)

```bash
curl -sf http://localhost:8123/healthz
curl -sf -X POST http://localhost:8123/egress/evaluate \
  -H 'content-type: application/json' \
  -d '{"flow_id":"demo-1","destination_host":"api.openai.com"}'
```

Allowlisted destination passes. Off-allowlist host is denied.

### 3. Spine commit + chain verify (90s)

```bash
curl -sf -X POST http://localhost:8120/governed/commit \
  -H 'content-type: application/json' \
  -d '{"platform":"egress_govern","operation_id":"demo-1","facets":{"flow_id":"demo-1","destination_host":"api.openai.com","egress_decision":"ALLOWED"},"policy_id":"egress-critical-us","reserved_budget":"0","committed_budget":"0","outcome":"allowed"}'

curl -sf -H 'x-internal-token: dev-cg-spine-token-change-me' \
  http://localhost:8121/internal/security/verify-chain
```

### 4. Close (30s)

- One canonical tree: `cybersecurity-governor/` (812x ports, Helm deploy)
- L4 Gold parity with MG/FG/IG — CI tiers 1–4 on GitHub Actions

## Reference docs

| Doc | Purpose |
|-----|---------|
| [docs/cybersecurity-governor/README.md](docs/cybersecurity-governor/README.md) | Quick start |
| [docs/cybersecurity-governor/security-enforcement-mesh.md](docs/cybersecurity-governor/security-enforcement-mesh.md) | Mesh + platforms |
| [docs/cybersecurity-governor/institutional-gold-standard.md](docs/cybersecurity-governor/institutional-gold-standard.md) | RFP / reliability |
| [deploy/helm/cybersecuritygovernor/](deploy/helm/cybersecuritygovernor/) | K8s + S3 anchor |
