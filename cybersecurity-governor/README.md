# Cybersecurity Governor

Institutional++ insurance control plane — **own spine** (gateway / sidecar / reconciler) with **Crystal Commit Protocol**, plus **extractable standalone platforms**.

## What this is

| Layer | Purpose |
|-------|---------|
| **Spine** | Optional shared governance: CCP, claim escrow, hash chain, `security_ops` invariants, horizon reconciler |
| **Platforms** | Standalone products (ClaimGate, …) that work alone or plug into spine via `SpineAdapter` |

ModelGovernor, Finance Governor, and Cybersecurity Governor are **sibling spines** — same reliability patterns, different domains.

## Architecture

```
cybersecurity-governor/
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
└── docs → ../docs/cybersecurity-governor/
```

## Deployment modes

| Mode | Compose | `CG_SPINE_ENABLED` |
|------|---------|-------------------|
| **Platform-only** | `platforms/claim_gate/docker-compose.standalone.yml` | `false` |
| **Spine-only** | `docker-compose.spine.yml` | n/a |
| **Full stack** | `docker-compose.yml` | `true` on platforms |

Platforms never require the spine. Set `CG_SPINE_ENABLED=false` for full standalone value.

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
make cg-spine-test

# Spine + ClaimGate
make cg-stack-up
make cg-spine-smoke
make claim-gate-demo

# Standalone ClaimGate only
cd platforms/claim_gate && docker compose -f docker-compose.standalone.yml up --build
```

## Institutional++ highlights (vs Finance Governor scaffold)

- Hash chain on **all** claim events including horizon sweeps (`security_seal.py`)
- `GET /internal/security/verify-chain` — 422 on tamper
- `security_ops.assert_security_ops_invariants()` — 7 probes, zero error budget
- Reconciler **halts sweeps** in diagnostic mode (ModelGovernor parity)
- `SpineAdapter` + `LocalPlatformEventLog` for standalone audit trail

Full spec: [docs/cybersecurity-governor/institutional-gold-standard.md](../docs/cybersecurity-governor/institutional-gold-standard.md)
