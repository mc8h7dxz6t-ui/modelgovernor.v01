# modelgovernor.v01

A production-grade, ledger-backed AI governance control plane for reliable spend control, policy enforcement, and auditable reconciliation across multi-provider and agentic workloads.

## Sales demo (start here — plug and play)

**No API keys. No cloud. ~5 minutes.** Full institutional++ walkthrough for prospects and evaluators.

```bash
make demo-prereqs-install   # once: Docker + Compose + curl + make
make demo-gold-up
make demo-gold
```

See [SALES-DEMO.md](SALES-DEMO.md) for the talk track, capability matrix, production upgrade path (`docs/plug-and-play.md`), and [platform sales sheets](docs/sales-sheets/).

```bash
make demo-gold-down   # teardown
```

## Finance Governor (platform design)

The **Finance Governor** ecosystem adapts this repository's institutional++ spine for regulated finance — as an **optional control plane** plus **five standalone platforms**, each solving a high-cost problem and deployable alone:

| Platform | Problem |
|----------|---------|
| **AlgoFreeze** | Runaway algo / bad deploy (Knight Capital-class) |
| **WireMatch** | Wrong wire / decimal error (Citigroup-class) |
| **SubledgerSync** | Intercompany reconciliation drift |
| **AssetLedger** | Stale asset depreciation |
| **CreditGovern** | Ungoverned credit AI |

- [Platform model — standalone or spine](docs/finance-governor/platform-model.md)
- [Finance Governor spine](docs/finance-governor/spine.md) — own gateway/sidecar/reconciler (`finance-governor/`)
- [Crystal Commit Protocol](docs/finance-governor/crystal-commit-protocol.md)
- [Desirability deep dive — ROI, buyers, GTM](docs/finance-governor/desirability.md)
- [Institutional++ gold standard — reliability & regulatory mapping](docs/finance-governor/institutional-gold-standard.md)
- [Code-driven finance fixes (deep dive)](docs/finance-governor/code-driven-fixes.md)
- [Platform vision](docs/finance-governor/README.md)

## Cybersecurity Governor (platform design)

The **Cybersecurity Governor** ecosystem adapts the institutional++ spine for security operations — closing **The Shadow Gap** (time-skew, ephemeral erasure, log mutation) with the **Threat Crystal Protocol (TCP)**:

| Platform | Problem |
|----------|---------|
| **IdentityGovern** | Session hijack / token binding mismatch |
| **EgressGovern** | Ungoverned data exfiltration |
| **ThreatProxy** | Log erasure / telemetry silence |

- [Platform vision](docs/cybersecurity-governor/README.md)
- [Cybersecurity Governor spine](docs/cybersecurity-governor/security-enforcement-mesh.md) — gateway/sidecar/reconciler (`cybersecurity-governor/`)
- [L4 certification](docs/cybersecurity-governor/l4-certification.md)
- [Operations runbook](docs/cybersecurity-governor/operations-runbook.md)

```bash
make cg-spine-test            # unit tests (SQLite)
make cg-certification-l4-ci   # L4 Gold CI gate
```

See [CYBER-SALES-DEMO.md](CYBER-SALES-DEMO.md) for the CISO talk track.

## What this repository demonstrates

- Reserve-before-dispatch governance semantics
- Append-only ledger event trail for material state transitions
- Replay-safe reserve/settle lifecycle
- Per-trace atomic cap enforcement
- Drift enforcement with deterministic wallet lockout
- Reconciler handling for expiry, stranded holds, and late settlement
- Internal-auth operational read APIs for wallet/operation/trace/audit state
- Internal-auth Prometheus-style metrics at `/metrics`

## Quick local demo (Docker Compose first)

Prerequisites: Docker + Docker Compose plugin, `make`, `curl`.

```bash
make demo-prereqs-install   # optional: install on Ubuntu/Debian/Fedora/RHEL
make demo-prereqs             # verify
```

```bash
make demo-up
make demo-smoke
make demo-drift-lock
make demo-status
```

Then inspect:

```bash
make demo-ledger
make demo-events
```

Internal operational surfaces (all require `x-internal-token`):

```bash
curl -H "x-internal-token: $SIDECAR_PRIMARY_TOKEN" http://localhost:8081/internal/wallet/demo-user
curl -H "x-internal-token: $SIDECAR_PRIMARY_TOKEN" http://localhost:8081/internal/events/recent?limit=20
curl -H "x-internal-token: $SIDECAR_PRIMARY_TOKEN" http://localhost:8081/internal/diagnostic/status
curl -X POST -H "x-internal-token: $SIDECAR_PRIMARY_TOKEN" http://localhost:8081/internal/diagnostic/clear
curl -H "x-internal-token: $SIDECAR_PRIMARY_TOKEN" http://localhost:8081/internal/ledger/verify-chain
curl -H "x-internal-token: $SIDECAR_PRIMARY_TOKEN" http://localhost:8081/metrics
```

Shutdown:

```bash
make demo-down
```

See `docs/demo.md` for full walkthrough and troubleshooting.

## Proof / reliability validation

Institutional++ **gold standard**: runtime anomaly probes, DB invariant backstops (`migrations/0005`–`0007`), Redis guardrails with graceful degradation, provider circuit breakers, OpenTelemetry-ready tracing, governance gateway, HTTP RED metrics, SLO burn-rate alerts, synthetic canary probes, property/chaos tests, and full K8s deploy manifests. See `docs/slo-definitions.md` and `docs/observability.md`.

Three tiers of testing are available. See `docs/reliability-testing.md` for full scenario tables, metrics reference, and CI integration examples.

### Tier 1 — Lightweight local checks (SQLite, < 1 second)

```bash
pytest -q tests/integration/test_ledger_hardening.py
pytest -q tests/programs/finance_ops_finals/
pytest -q tests/programs/cost_attribution_accountability/
```

### Tier 2 — Postgres vigorous proof (real DB semantics)

```bash
docker compose -f docker-compose.test.yml up -d postgres-test
export POSTGRES_TEST_URL=postgresql+psycopg://postgres:postgres@localhost:5433/mg_test
pytest -q tests/integration/test_postgres_vigorous.py
```

### Tier 3 — Load harness (SQLite or Postgres)

```bash
pytest -q tests/load/test_load_harness.py
# or run all scenarios and write a JSON report:
python tests/load/test_load_harness.py
```

Reports are written to `tests/load/reports/`.

### Production HA (Finance Ops Finals)

```bash
docker compose -f docker-compose.ha.yml up -d --scale sidecar=3 --scale reconciler=2
kustomize build deploy/overlays/production | kubectl apply --dry-run=client -f -
```

See `docs/ha-strategy.md`, `docs/pgbouncer-runbook.md`, `docs/gitops.md`, `programs/finance_ops_finals/README.md`.

### Tier 4 — Toxiproxy chaos (Finance Ops, Postgres)

```bash
docker compose -f docker-compose.chaos.yml up -d
export POSTGRES_TEST_URL=postgresql+psycopg://postgres:postgres@localhost:5435/mg_chaos
pytest -q tests/chaos/test_toxiproxy_finance_ops.py
```

### Invariant report (optional)

```bash
python scripts/generate_invariant_report.py --operations 120 --workers 12
```

Output: `artifacts/reliability/latest_invariant_report.json`

## Command surface

```bash
make demo-up
make demo-down
make demo-reset
make demo-smoke
make demo-drift-lock
make demo-status
make demo-ledger
make demo-events
make proof-test
make load-test
```

## Diligence-oriented docs

- `docs/sales-sheets/` — full spec, maturity tiers, and IL rubric per platform
- `LICENSE` (license posture)
- `docs/dependency-licenses.md` (dependency/license visibility)
- `docs/transferability.md` (portability and operational cleanliness)
- `docs/reliability-testing.md` (proof tiers and invariant artifacts)

## Repository layout

```text
README.md
LICENSE
Makefile
.env.example
docker-compose.yml
docker-compose.test.yml
docker-compose.ha.yml
docker-compose.chaos.yml

deploy/
  argocd/               # ArgoCD AppProject + Applications (GitOps)
  helm/modelgovernor/   # Helm chart (alternative to kustomize overlays)
  base/                 # K8s manifests, PgBouncer, migration job, Prometheus rules
  overlays/
    staging/
    production/
docs/
gateway/
migrations/
reconciler/
scripts/
sidecar/
  app/
    metrics.py          # invariant counter registry
tests/
  programs/
    algofreeze/                      # AlgoFreeze — network freeze for live algos
    wire_match/                      # WireMatch — semantic cross-border wire gate
    subledger_sync/                  # SubledgerSync — intercompany reconciliation
    asset_depreciation/              # AssetLedger — smart asset depreciation
    finance_governor/                # CreditGovern — credit decision wedge (design)
    finance_ops_finals/              # AI Finance Ops Finals for LLMs
    cost_attribution_accountability/ # AI Cost Attribution & Agent Accountability
finance-governor/                    # Finance Governor spine + platforms
cybersecurity-governor/              # Cybersecurity Governor spine + platforms (canonical)
  integration/
    conftest.py         # Postgres session fixtures
    test_postgres_vigorous.py
  load/
    test_load_harness.py
```

## Precision note

Load-harness outputs in this repository are correctness/invariant artifacts. They are intentionally not presented as universal throughput or latency claims.
