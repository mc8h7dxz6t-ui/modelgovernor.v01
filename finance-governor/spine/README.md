# Finance Governor Spine

The **Finance Governor Spine** is a dedicated control plane — structurally parallel to ModelGovernor (`gateway` / `sidecar` / `reconciler`) but domain-adapted for regulated finance and built around the **Crystal Commit Protocol (CCP)**.

ModelGovernor spine governs **LLM reserve → dispatch → settle**.  
Finance Governor spine governs **crystallize → act → commit** across all finance platforms.

## Topology

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Finance Governor Spine                              │
│                                                                          │
│  ┌──────────────┐    ┌─────────────────────┐    ┌──────────────────┐  │
│  │   Gateway    │───►│   Ledger Sidecar    │◄───│   Reconciler     │  │
│  │   :8090      │    │   :8091             │    │   :8092          │  │
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
| **gateway** | 8090 | `gateway/` | Finance Decision API; platform orchestration |
| **sidecar** | 8091 | `sidecar/` | CCP ledger, commit escrow, regulatory_ops |
| **reconciler** | 8092 | `reconciler/` | Horizon sweep, strand, crystal mesh audit |

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
finance-governor/
├── spine/
│   ├── gateway/          # OIDC, /governed/commit, platform proxy
│   ├── sidecar/          # CCP ledger, routes, regulatory_ops
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
adapter = SpineAdapter(base_url="http://fg-sidecar:8091", platform="wire_match")
crystal = adapter.crystallize(operation_id="wire-123", risk_tier="critical", facets={...})
# ... platform acts ...
adapter.commit(crystal_id=crystal.crystal_id, outcome={...})
```

With `FG_SPINE_ENABLED=false`, adapter writes to local `platform_crystals` — same envelope, no spine dependency.

## Docs

- [Spine architecture (full spec)](../../docs/finance-governor/spine.md)
- [Crystal Commit Protocol](../../docs/finance-governor/crystal-commit-protocol.md)
- [Spine port map](../../docs/finance-governor/spine-port-map.md)

## Quick start (when implemented)

```bash
cd finance-governor
cp .env.example .env
docker compose up -d
curl http://localhost:8091/healthz
```
