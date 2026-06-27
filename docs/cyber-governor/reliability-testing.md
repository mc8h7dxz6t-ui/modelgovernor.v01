# Reliability testing — Cybersecurity Governor

Institutional++ test pyramid aligned with ModelGovernor / Finance Governor quality bar.

## Quick gates

| Target | Command | Tier |
|--------|---------|------|
| Unit + hardening + chaos (SQLite) | `make cg-spine-test` | 1 + 4-lite |
| Property (Hypothesis hash chain) | `make cg-property-test` | 1+ |
| Postgres integration | `make cg-postgres-test` | 2 |
| Load harness | `make cg-load-test` (requires `CG_LOAD_TEST=1`) | 3 |
| Toxiproxy network chaos | `make cg-chaos-test` | 4 |
| Invariant JSON report | `make cg-invariant-report` | probe |
| Full proof bundle | `make cg-proof-test` | 1–3 + property + deploy |

## Tier 1 — SQLite unit + spine hardening (< 3s)

```bash
cd cyber-governor && make cg-spine-test
```

**Modules (42+ tests):**

| File | Coverage |
|------|----------|
| `tests/test_crystal.py` | Threat Crystal seal / fingerprint |
| `tests/test_spine_lifecycle.py` | Crystallize → commit lifecycle |
| `tests/test_spine_hardening.py` | Happy path, idempotent replay, fingerprint mismatch, horizon strand, mesh block, budget cap, sweep+chain, anchor head |
| `tests/test_mesh_block.py` | Threat mesh STRANDED → egress block |
| `tests/test_horizon_sweep.py` | Expired horizon → STRANDED_HOLD + valid chain |
| `tests/test_security_chain.py` | Hash chain verify + anchor API |
| `tests/test_security_anchor_s3.py` | S3 WORM anchor mock |
| `tests/test_invariants.py` | `security_ops` / `threat_ops` invariant probes |
| `tests/test_diagnostic_mode.py` | Redis diagnostic latch |
| `tests/test_lineage.py` | Lineage DAG helpers |
| `tests/test_lineage_ingest.py` | Falco/Tetragon/generic ingest |
| `tests/test_identity_gate.py` | Session arm / hijack STRANDED |
| `tests/test_egress_lock.py` | Egress evaluate / block |
| `tests/test_witness_bridge.py` | CloudTrail / generic witness |
| `tests/integration/test_readiness.py` | `/healthz`, `/readyz`, `/metrics.json` |
| `tests/integration/test_platforms_smoke.py` | All 4 platform health + core APIs |
| `tests/integration/test_chaos_resilience.py` | 24 concurrent crystallize/commit, chain + invariants |

## Property tests (Hypothesis)

```bash
make cg-property-test
```

| File | Coverage |
|------|----------|
| `tests/test_property_security_chain.py` | Append N events → valid chain; tampered row_hash/prev_hash; hash determinism; crystallize replay |

## Tier 2 — Postgres vigorous

```bash
docker compose -f docker-compose.test.yml up -d
export CG_POSTGRES_TEST_URL=postgresql+psycopg://postgres:postgres@localhost:5444/cg_test
make cg-postgres-test
```

**Modules:**

| File | Coverage |
|------|----------|
| `tests/integration/test_postgres_vigorous.py` | JSONB facets, ENUM status, CHECK constraints, concurrent sweep `SKIP LOCKED`, concurrent crystallize idempotency, lineage persist |
| `tests/integration/test_migration_invariants.py` | Migration files present, escrow non-negative CHECK on Postgres |

`clean_cg_tables` fixture truncates and re-seeds `control_policy_registry`, `threat_mesh_rules`, and `principal_budgets` between tests.

## Tier 3 — Load harness

```bash
CG_LOAD_TEST=1 CG_LOAD_RPS=50 CG_LOAD_DURATION=3 make cg-load-test
```

`tests/load/test_cg_load_harness.py` — concurrent crystallize/commit under configurable RPS/workers; asserts zero errors, hash chain valid, p99 &lt; 5s, achieved RPS ≥ 50% of target.

## Tier 4 — Toxiproxy network chaos

```bash
docker compose -f docker-compose.chaos.yml up -d --wait cg-postgres-chaos cg-toxiproxy
docker compose -f docker-compose.chaos.yml run --rm cg-toxiproxy-config
make cg-chaos-test
```

**Modules:**

| File | Coverage |
|------|----------|
| `tests/chaos/test_toxiproxy_cyber_ops.py` | Latency survival, connection timeout + recovery, burst under latency + invariants |

Env: `CG_CHAOS_POSTGRES_URL` (proxied `:5446`), `TOXIPROXY_API` (`:8475`).

## Tier 5 — Live demo / smoke

```bash
make cg-stack-up
make cg-security-demo
make cg-spine-smoke
```

## Tier 6 — K8s manifest gate

```bash
make cg-deploy-dry-run
# or: kustomize build deploy/base/ | kubectl apply --dry-run=client -f -
```

## Invariant report

```bash
make cg-invariant-report
# writes reports/cyber-invariant-report.json
```

## Invariant probes (zero error budget)

| Probe | Module | Trigger |
|-------|--------|---------|
| Negative principal balance | `security_ops` | Post-reconciler sweep |
| Action cap overrun | `security_ops` | Post-reconciler sweep |
| Commit without crystal | `threat_ops` | Post-reconciler sweep |
| Duplicate commit events | `threat_ops` | Post-reconciler sweep |
| High-risk silent expire | `threat_ops` | Post-reconciler sweep |

On violation: `enter_diagnostic_mode()` + `security_audit_violation_total` increment.

## CI

`.github/workflows/ci.yml` jobs:
- `cyber-governor-test` — Tier 1, property, Tier 2, invariant report, Kustomize
- `cyber-governor-chaos` — Tier 4 Toxiproxy (latency, timeout recovery)
