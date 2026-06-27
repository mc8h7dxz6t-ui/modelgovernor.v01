# Cybersecurity Governor Spine

The **Cybersecurity Governor Spine** is a dedicated control plane — structurally parallel to ModelGovernor (`gateway` / `sidecar` / `reconciler`) but domain-adapted for regulated finance and built around the **Threat Crystal Protocol (CCP)**.

ModelGovernor spine governs **LLM reserve → dispatch → settle**.  
Cybersecurity Governor spine governs **crystallize → act → commit** across all finance platforms.

## Topology

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Cybersecurity Governor Spine                              │
│                                                                          │
│  ┌──────────────┐    ┌─────────────────────┐    ┌──────────────────┐  │
│  │   Gateway    │───►│   Ledger Sidecar    │◄───│   Reconciler     │  │
│  │   :8100      │    │   :8101             │    │   :8102          │  │
│  │ OIDC, orch   │    │ CCP, escrow, events │    │ horizon sweep    │  │
│  └──────┬───────┘    └──────────┬──────────┘    └────────┬─────────┘  │
│         │                       │                         │             │
└─────────┼───────────────────────┼─────────────────────────┼─────────────┘
          │                       │                         │
          ▼                       ▼                         ▼
   Finance platforms         PostgreSQL 16              Redis 7
   (optional adapters)      (sole SoT)                (volatile only)
```

## Services

| Service | Port | ModelGovernor analog | Finance adaptation |
|---------|------|---------------------|-------------------|
| **gateway** | 8100 | `gateway/` | Finance Decision API; platform orchestration |
| **sidecar** | 8101 | `sidecar/` | CCP ledger, commit escrow, security_ops |
| **reconciler** | 8102 | `reconciler/` | Horizon sweep, strand, crystal mesh audit |

Ports intentionally offset from ModelGovernor (8080–8082) so both stacks can run side-by-side in dev.

## Lifecycle (CCP-native)

```
1. CRYSTALLIZE  POST /crystallize     → governance_crystal + optional exposure reserve
2. ACT          Platform executes     → algo / wire / match / depreciate / score
3. COMMIT       POST /commit          → crystal-bound terminal state
   or STRAND    Reconciler on horizon → never guess on critical/high risk
4. ADJUDICATE   POST /adjudicate      → compliance resolution of STRANDED
```

## Directory layout

```
cyber-governor/
├── spine/
│   ├── gateway/          # OIDC, /governed/commit, platform proxy
│   ├── sidecar/          # CCP ledger, routes, security_ops
│   └── reconciler/       # horizon sweeper, mesh audit
├── platforms/
│   └── common/           # spine_adapter.py, crystal.py (shared by all platforms)
├── migrations/           # spine schema
├── deploy/               # K8s overlays (Phase 3)
└── docker-compose.yml
```

## Platform integration

Platforms call the spine via `platforms/common/spine_adapter.py`:

```python
adapter = SpineAdapter(base_url="http://cg-sidecar:8101", platform="wire_match")
crystal = adapter.crystallize(operation_id="wire-123", risk_tier="critical", facets={...})
# ... platform acts ...
adapter.commit(crystal_id=crystal.crystal_id, outcome={...})
```

With `CG_SPINE_ENABLED=false`, adapter writes to local `platform_crystals` — same envelope, no spine dependency.

## Docs

- [Spine architecture (full spec)](../../docs/cyber-governor/spine.md)
- [Threat Crystal Protocol](../../docs/cyber-governor/crystal-commit-protocol.md)
- [Spine port map](../../docs/cyber-governor/spine-port-map.md)

## Quick start (when implemented)

```bash
cd cyber-governor
cp .env.example .env
docker compose up -d
curl http://localhost:8101/healthz
```
