# Cybersecurity Governor Spine — Architecture

Canonical specification for the **Cybersecurity Governor spine** — a ModelGovernor-parallel control plane adapted for security operations and centered on the **Threat Crystal Protocol (TCP)**.

## Overview

- **Gateway** (:8100) — normalizes platform requests; orchestrates crystallize → act → commit
- **Ledger sidecar** (:8101) — enforces TCP, action escrow, crystal-bound commit, replay protection
- **Postgres** — threat crystal chain, security_events hash chain, audit SoT
- **Redis** — volatile guardrails only (rate limits, diagnostic flag)
- **Reconciler** (:8102) — horizon sweep, strand ambiguous sessions, security_ops audit

## Sibling relationship

| Aspect | ModelGovernor | Finance Governor | Cybersecurity Governor |
|--------|---------------|------------------|------------------------|
| Pre-action | Reserve | Crystallize | Crystallize (arm) |
| Terminal | Settle | Commit | Commit (authorize) |
| Crystal | — | Governance Crystal | Threat Crystal |
| Unique IP | Adaptive Reservation | CCP | TCP + Threat Mesh |
| Ports | 8080–8082 | 8090–8092 | 8100–8102 |

## Request lifecycle

```
1. CRYSTALLIZE  POST /crystallize     → threat_crystal + optional action budget
2. ACT          Platform executes     → session arm / egress / witness ingest
3. COMMIT       POST /commit          → crystal-bound terminal state
   or STRAND    Reconciler on horizon → never guess on critical/high
```

## Core tables

| Table | Purpose |
|-------|---------|
| `threat_crystals` | TCP envelope — facets, horizon, hash chain |
| `action_escrow_ledger` | Per-operation state machine |
| `security_events` | Append-only audit + row hash |
| `principal_budgets` | Action budget per tenant/principal |
| `control_policy_registry` | Platform + risk tier + horizons |
| `threat_mesh_rules` | Cross-platform parent→child blocks |

## Sidecar API

### Mutation (internal token)

| Endpoint | Purpose |
|----------|---------|
| `POST /crystallize` | Create threat crystal |
| `POST /commit` | Crystal-bound authorize |

### Read

| Endpoint | Purpose |
|----------|---------|
| `GET /internal/crystals/{id}/reconstruct` | Forensic reconstruction bundle |
| `GET /internal/events/recent` | Append-only audit |
| `GET /internal/diagnostic/status` | Write-halt state |

## Invariants (zero error budget)

| Invariant | Counter |
|-----------|---------|
| No commit without crystal | `surprise_authorize_blocked_total` |
| Fingerprint match at commit | `threat_fingerprint_mismatch_total` |
| Critical/high horizon → strand | `threat_horizon_strand_total` |
| Mesh rule violation blocked | `threat_mesh_block_total` |

## Deployment

```bash
make cg-spine-up
docker compose up -d
curl http://localhost:8101/healthz
```

See [platform-model.md](platform-model.md) and [integrations.md](integrations.md).
