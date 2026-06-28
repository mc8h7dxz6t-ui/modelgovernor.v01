# Platform A — Sales Demo (Gold Standard)

**SKU:** `MG-PLATFORM-DEMO`  
**Tagline:** Zero-setup institutional++ walkthrough for prospects, investors, and conference booths.

---

## Executive summary

A **Docker-only**, **zero external dependency** stack that runs the full ModelGovernor control-plane topology in mock mode. Prospects execute `make demo-gold` and see reserve-before-dispatch governance, multi-provider routing, tamper-evident ledger, diagnostic mode, and SLO metrics in ~3 minutes.

| | |
|---|---|
| **Target buyer** | VP Eng, Head of AI Platform, CFO office (AI spend), enterprise architects |
| **Sales motion** | Top-of-funnel, diligence calls, bake-offs vs LiteLLM / homegrown |
| **Time to live** | 5 minutes (first build ~2 min) |
| **Maturity tier** | **L4 demo** — `make demo-gold` |

---

## Full technical specification

### Topology

```
┌─────────────┐     ┌─────────────┐     ┌──────────────┐
│   Gateway   │────▶│   Sidecar   │────▶│  PostgreSQL  │
│  :8080      │     │  :8081      │     │  :5432       │
│ mock providers    │ policy+ledger     │ authoritative│
└─────────────┘     └──────┬──────┘     └──────────────┘
                           │
                    ┌──────▼──────┐     ┌──────────────┐
                    │    Redis    │     │ Reconciler   │
                    │  :6379      │     │  :8082       │
                    └─────────────┘     └──────────────┘
```

### Services (docker-compose.demo.yml)

| Service | Image / build | Port | Health |
|---|---|---|---|
| postgres | postgres:16 | 5432 | pg_isready |
| redis | redis:7-alpine | 6379 | redis-cli ping |
| sidecar | sidecar/Dockerfile | 8081 | GET /healthz |
| gateway | gateway/Dockerfile | 8080 | GET /healthz |
| reconciler | reconciler/Dockerfile | 8082 | GET /healthz |

### Configuration (demo defaults)

| Variable | Value | Notes |
|---|---|---|
| `PROVIDER_MODE` | `mock` | OpenAI / Anthropic / Vertex paths without API keys |
| `OIDC_ENABLED` | `false` | Internal token auth |
| `GUARDRAILS_ENABLED` | `true` | Redis rate limits active |
| `CIRCUIT_BREAKER_ENABLED` | `true` | Provider storm protection |
| `MOCK_DISPATCH_COST` | `1.000000` | Deterministic settle amounts |
| Migrations | `0001`–`0011` auto-applied | Full institutional schema |

### API surfaces demonstrated

| Step | Endpoint | Capability proven |
|---|---|---|
| 1 | `GET /readyz` (×3) | HA readiness chain |
| 2 | `POST /governed/dispatch` | Reserve → provider → settle |
| 3 | Multi-model dispatch | Provider router (mock) |
| 4 | `GET /internal/ledger/verify-chain` | Hash-chain integrity |
| 5 | Diagnostic mode + `POST /internal/diagnostic/clear` | No poison-pill ops |
| 6 | `GET /metrics/prometheus` | SLO / RED metrics |
| 7 | `GET /internal/wallet`, `/internal/events/recent` | Authoritative ledger |

### Included artifacts

- `SALES-DEMO.md` — quick start
- `docs/sales-demo.md` — talk track
- `scripts/demo-gold.sh` — 7-step scripted walkthrough
- `docs/capability-matrix.md` — RFP table
- `docs/plug-and-play.md` — upgrade path slide

### Requirements

| Requirement | Minimum |
|---|---|
| Docker + Compose v2 | Required |
| CPU / RAM | 2 cores, 4 GB |
| Network | None (fully offline after image pull) |
| API keys | None |
| Kubernetes | Not required |

### Commands

```bash
make demo-gold-up    # start stack + migrations
make demo-gold       # live walkthrough
make demo-gold-down  # teardown
```

---

## Commercial packaging

### What the buyer gets

- Reproducible demo environment for unlimited internal showings
- Scripted narrative aligned to enterprise pain (runaway AI spend, audit, incident response)
- Production flip chart (env vars + overlays) at end of demo

### Competitive positioning

| vs. | Demo advantage |
|---|---|
| LiteLLM dashboard | Live **pre-dispatch reserve**, not post-hoc logs |
| Slides-only pitch | Runnable proof in buyer's laptop |
| Cloud-only budget alerts | Shows **governance gateway** pattern |

### Evaluation path

| Package | Deliverable |
|---|---|
| Open eval | Repo + `make demo-gold` |
| Guided eval call | SE runs demo on Zoom |
| Executive briefing | On-site demo + architecture Q&A (1 day) |

---

## Maturity proof

| Component | Verified by |
|---|---|
| Compose stack + migration automation | `make demo-gold-up` |
| Scripted 7-step sales walkthrough | `make demo-gold` |
| Talk track + capability matrix | [SALES-DEMO.md](../../SALES-DEMO.md) |

**Strategic value:** Shortens sales cycle vs build-your-own-demo; required for institutional outbound motion.

---

## Upgrade path

→ **Platform B (Staging / Pilot)** when buyer provides K8s + secrets  
→ **Platform C (Production)** for regulated production traffic

See [02-staging-pilot-platform.md](02-staging-pilot-platform.md).
