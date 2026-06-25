# Insurance Governor

Institutional++ insurance control plane — **own spine** (gateway / sidecar / reconciler) with **Crystal Commit Protocol**, plus **extractable standalone platforms**.

## What this is

| Layer | Purpose |
|-------|---------|
| **Spine** | Optional shared governance: CCP, claim escrow, hash chain, `claim_ops` invariants, horizon reconciler |
| **Platforms** | Standalone products (ClaimGate, …) that work alone or plug into spine via `SpineAdapter` |

ModelGovernor, Finance Governor, and Insurance Governor are **sibling spines** — same reliability patterns, different domains.

## Architecture

```
insurance-governor/
├── spine/                 # Optional control plane (ports 8100–8102)
│   ├── gateway/
│   ├── sidecar/
│   └── reconciler/
├── platforms/             # Extractable wedges
│   ├── common/            # crystal.py, spine_adapter.py
│   └── claim_gate/        # Phase 1 payout gate
├── migrations/
├── docker-compose.yml     # Full stack
├── docker-compose.spine.yml
└── docs → ../docs/insurance-governor/
```

## Deployment modes

| Mode | Compose | `IG_SPINE_ENABLED` |
|------|---------|-------------------|
| **Platform-only** | `platforms/claim_gate/docker-compose.standalone.yml` | `false` |
| **Spine-only** | `docker-compose.spine.yml` | n/a |
| **Full stack** | `docker-compose.yml` | `true` on platforms |

Platforms never require the spine. Set `IG_SPINE_ENABLED=false` for full standalone value.

## Ports

| Service | Port |
|---------|------|
| ig-gateway | 8100 |
| ig-sidecar | 8101 |
| ig-reconciler | 8102 |
| claim-gate | 8103 |

## Quick start

```bash
# Tests (Tier 1 — SQLite)
make ig-spine-test

# Spine + ClaimGate
make ig-stack-up
make ig-spine-smoke
make claim-gate-demo

# Standalone ClaimGate only
cd platforms/claim_gate && docker compose -f docker-compose.standalone.yml up --build
```

## Institutional++ highlights (vs Finance Governor scaffold)

- Hash chain on **all** claim events including horizon sweeps (`claim_seal.py`)
- `GET /internal/claims/verify-chain` — 422 on tamper
- `claim_ops.assert_claim_ops_invariants()` — 7 probes, zero error budget
- Reconciler **halts sweeps** in diagnostic mode (ModelGovernor parity)
- `SpineAdapter` + `LocalPlatformEventLog` for standalone audit trail

Full spec: [docs/insurance-governor/institutional-gold-standard.md](../docs/insurance-governor/institutional-gold-standard.md)
