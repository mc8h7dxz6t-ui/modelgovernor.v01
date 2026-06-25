# Finance Governor Spine

Concrete file-level guide for copying ModelGovernor into `finance-governor/spine/`.

**Canonical spine spec:** [spine.md](spine.md)

## Target layout

```
finance-governor/
├── spine/
│   ├── gateway/          ← modelgovernor/gateway/
│   ├── sidecar/          ← modelgovernor/sidecar/
│   └── reconciler/       ← modelgovernor/reconciler/
├── platforms/common/     ← crystal.py, spine_adapter.py (done)
└── migrations/           ← 0001_fg_spine_init.sql (done)
```

## Copy verbatim (rename only)

| ModelGovernor | Finance Governor | Notes |
|---------------|------------------|-------|
| `sidecar/app/diagnostic_mode.py` | same | Write halt semantics identical |
| `sidecar/app/circuit_breaker.py` | same | Rail failures, not provider |
| `sidecar/app/fallback_limiter.py` | same | Redis degradation |
| `sidecar/app/auth_oidc.py` | same | Add finance RBAC roles |
| `sidecar/app/http_metrics.py` | same | Rename metric prefix |
| `sidecar/app/tracing.py` | same | Baggage: application_id |
| `reconciler/app/leader.py` | same | Advisory lock unchanged |
| `reconciler/app/health_server.py` | same | |
| `sidecar/app/db.py`, `config.py` | same | |
| `deploy/base/prometheus-rules.yaml` | same | Rename alerts |
| `deploy/base/pgbouncer.yaml` | same | |
| `docker-compose.ha.yml` pattern | same | |

## Adapt (domain substitution)

| ModelGovernor | Finance Governor | Changes |
|---------------|------------------|---------|
| `sidecar/app/ledger.py` | `decision_ledger.py` | wallets→accounts, tokens→exposure, model→policy |
| `sidecar/app/finance_ops.py` | `regulatory_ops.py` | + high_risk_auto_expired, version mismatch |
| `sidecar/app/ledger_seal.py` | `decision_seal.py` | table: decision_events |
| `sidecar/app/attribution.py` | `attribution.py` | + desk_id, book_id, application_id |
| `sidecar/app/policy.py` | `policy.py` | instrument_policy_registry |
| `sidecar/app/guardrails.py` | `guardrails.py` | per-desk limits |
| `sidecar/app/money.py` | `currency.py` | ISO 4217 quantum |
| `sidecar/app/routes_reserve.py` | `routes_crystallize.py` | CCP entry + exposure reserve |
| `sidecar/app/routes_settle.py` | `routes_commit.py` | Crystal-bound commit |
| `gateway/app/governance.py` | `governance.py` | crystallize → act → commit |
| `gateway/app/pricing.py` | `exposure_estimator.py` | approval probability bounds |
| `reconciler/app/sweeper.py` | `sweeper.py` | high-risk strand rules |
| `migrations/0001_init.sql` | `0001_init.sql` | see domain-model.md |

## New (finance-specific)

| Module | Purpose |
|--------|---------|
| `routes_adjudicate.py` | Compliance officer STRANDED resolution |
| `routes_regulatory.py` | Examiner export bundle |
| `bias_monitor.py` | Cohort counters on settlement |
| `model_ownership.py` | Accountability registry CRUD |

## Test port map

| ModelGovernor test | Finance Governor test |
|--------------------|----------------------|
| `tests/integration/test_property_ledger.py` | `test_property_decision_ledger.py` |
| `tests/programs/finance_ops_finals/` | `tests/programs/finance_governor/` |
| `tests/chaos/test_toxiproxy_finance_ops.py` | `test_toxiproxy_regulatory_ops.py` |
| `tests/programs/cost_attribution_accountability/` | `test_credit_attribution.py` |

## Metric prefix rename

```
modelgovernor_*  →  financegovernor_*
```

Keep invariant event names parallel:

```
negative_wallet_detected_total     → negative_balance_detected_total
trace_cap_overrun_detected_total   → exposure_cap_overrun_detected_total
finance_audit_violation_total      → regulatory_audit_violation_total
```

## Demo script port

| ModelGovernor | Finance Governor |
|---------------|------------------|
| `scripts/demo-gold.sh` | `scripts/fg-demo-gold.sh` |
| `make demo-gold` | `make fg-demo-gold` |
| Mock LLM provider | Mock credit inference rail |

## Recommended copy procedure

1. Tag ModelGovernor release (e.g. `mg-spine-v1.0`)
2. `cp -r sidecar finance-governor/sidecar` — then domain substitution
3. Run port map checklist before first commit
4. Keep shared test fixtures for ledger property tests
5. Do not fork — document deltas in this file
