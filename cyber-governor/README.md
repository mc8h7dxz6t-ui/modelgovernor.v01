# Cybersecurity Governor

Institutional++ security control plane — **own spine** (gateway / sidecar / reconciler) adapted from ModelGovernor, with **Threat Crystal Protocol (TCP)** and optional standalone platforms.

Closes the **Shadow Gap**: time-skewed, ephemeral, and mutable evidence that blinds multi-vector IR.

## What this is

| Layer | Purpose |
|-------|---------|
| **Spine** | Shared governance: TCP, action escrow, hash chain, security_ops, horizon reconciler |
| **Platforms** | Standalone products that optionally plug into spine via `CG_SPINE_ENABLED` |

ModelGovernor, Finance Governor, and Cybersecurity Governor are **sibling spines** — same reliability patterns, different domains.

## Architecture

```
cyber-governor/
├── spine/                 # Security-adapted control plane
│   ├── gateway/           # :8100
│   ├── sidecar/           # :8101
│   └── reconciler/        # :8102
├── platforms/             # Standalone wedges + common adapter
│   ├── common/            # threat_crystal.py, spine_adapter.py, integrations.py
│   ├── identity_gate/     # Session hijack / token binding (:8103)
│   ├── egress_lock/       # Data exfil gate (:8104)
│   └── witness_bridge/    # Universal webhook ingest (:8105)
├── migrations/
├── docker-compose.yml
└── docs → ../docs/cyber-governor/
```

Full specification: [docs/cyber-governor/spine.md](../docs/cyber-governor/spine.md)

## Threat Crystal Protocol

Every irreversible security action on the spine requires a **Threat Crystal**:

- **Threat Crystal** — immutable, hash-chained snapshot of identity/lineage/posture at arm time
- **Session Horizon** — risk-tiered TTL; ambiguity **strands**, never guesses
- **Threat Mesh** — cross-platform invariants (e.g. STRANDED session blocks egress commit)
- **Forensic Reconstruction** — rebuild decision context without re-running sensors

See [threat-crystal-protocol.md](../docs/cyber-governor/threat-crystal-protocol.md).

## Standalone vs spine-connected

```bash
# Standalone — platform only, local threat crystals (no Postgres spine)
CG_SPINE_ENABLED=false uvicorn platforms.identity_gate.main:app --port 8103

# Full stack — spine + all platforms
make cg-stack-up
make cg-spine-test
make threat-crystal-demo
```

Platforms work with **most systems** via:

- HTTP JSON APIs (identity arm, egress evaluate)
- `POST /ingest/{source}` on WitnessBridge (`okta`, `cloudtrail`, `generic`)
- Optional spine adapter (`platforms/common/spine_adapter.py`)

## Status

| Component | Status |
|-----------|--------|
| Spine schema (`migrations/0001`) | ✅ |
| `platforms/common/threat_crystal.py` | ✅ TCP module |
| `platforms/common/integrations.py` | ✅ Okta / CloudTrail / generic normalizer |
| Spine services (gateway/sidecar/reconciler) | ✅ |
| IdentityGate, EgressLock, WitnessBridge | ✅ |
| Integration tests | ✅ |
| Witness quorum (S3 anchors) | ✅ |
| Lineage ingest (Falco/Tetragon) | ✅ |
| K8s deploy kit | ✅ `deploy/base/` |

```bash
make cg-stack-up
make cg-spine-test
make cg-security-demo
make lineage-ingest-demo
make identity-gate-demo
make egress-lock-demo
make witness-bridge-demo
```

## Environment

```bash
cp .env.example .env
# POSTGRES_DB=cybersecuritygovernor
# CG_SIDECAR_URL=http://localhost:8101
# CG_SPINE_ENABLED=true
```

## Ports (side-by-side with ModelGovernor / Finance Governor)

| Service | Port |
|---------|------|
| Gateway | 8100 |
| Sidecar | 8101 |
| Reconciler | 8102 |
| IdentityGate | 8103 |
| EgressLock | 8104 |
| WitnessBridge | 8105 |
| LineageIngest | 8106 |
| Postgres | 5443 |
| Redis | 6390 |
