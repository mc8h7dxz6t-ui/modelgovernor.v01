# Governor Spine — Disaster Recovery Runbook

**Classification:** Operational runbook — business continuity & fault isolation  
**Compliance mapping (inherent design):** BCBS 239 data lineage, FCA operational resilience patterns, NIST CSF recover  
**Maturity:** Institutional Self-Check Certified (`make plug`) — not third-party BC audit  
**Authoritative contract:** `governor-spine-core/spine_core/mode_contract.py`

---

## 1. Document control

| Field | Value |
|-------|-------|
| Repository layer | `governor-spine-core/` + per-governor `spine/sidecar/` |
| Failover model | **In-process degradation** — circuit breaker, local fallback, diagnostic halt |
| RTO (runtime redirect) | Sub-second for local fallback paths (no cross-cluster patch) |
| RTO (full Redis/Postgres restore) | Operator-dependent — typically minutes |
| RPO (ledger integrity) | **0 dropped sealed events** — Postgres authoritative; reconciler idempotent |

**Explicit non-pattern:** Do **not** patch Kubernetes deployments to `PROVIDER_MODE=mock` based on external `curl` health checks. Failover is **sidecar-local** and **operator-driven** for mode restoration.

---

## 2. Failure detection (implemented telemetry)

Sidecars expose Prometheus counters used in Helm canary CronJobs (e.g. `fg-governance-canary`, CG governance canary hitting `verify-chain`).

| Signal | Counter / probe | Typical response |
|--------|-----------------|----------------|
| Redis guardrail errors | `guardrail_degraded_total` | Local fallback limiter |
| Dependency storm | `dependency_circuit_open_total` | Circuit opens; local fallback |
| Finance / security invariant break | diagnostic alert | Diagnostic mode → writes `503` |
| Chain tamper | `verify-chain` `valid: false` | CronJob fails; operator forensics |
| Reconciler partition | leader election metric | Standby idle |

```
  [ rolling window — circuit_breaker_window_seconds ]
  
  Redis ping failures          Guardrail errors           verify-chain invalid
         │                            │                          │
         └────────────────────────────┼──────────────────────────┘
                                      ▼
                    circuit opens → local fallback OR diagnostic halt
```

Implementation: `circuit_breaker.py`, `guardrails.py`, `fallback_limiter.py`, `diagnostic_mode.py` in each governor sidecar.

---

## 3. Mode contract (no global singleton)

Degradation knobs are **environment variables** documented in `failover_env_contract()`:

```python
# governor-spine-core/spine_core/mode_contract.py
from spine_core.mode_contract import (
    RuntimeExecutionMode,
    resolve_provider_mode,
    resolve_spine_attachment,
    failover_env_contract,
)
```

| Transition | Trigger | Effect |
|------------|---------|--------|
| Active → degraded (automatic) | Redis failures exceed threshold | Circuit opens; local in-process limits |
| Active → diagnostic | Operator or finance/security audit | Crystallize/commit/reserve return `503` |
| Live → mock (ModelGovernor) | `PROVIDER_MODE=mock` | Gateway uses stub providers |
| Spine → standalone | `FG_SPINE_ENABLED=false` etc. | Platform local SQLite adapter |

**There is no `InstitutionalModeController` singleton.** Mode is resolved per-request from env + existing sidecar state machines.

---

## 4. Kubernetes operations (real patterns)

### Automated (safe)

- **Synthetic canaries** query in-cluster `/readyz` and `/internal/*/verify-chain` — see `deploy/helm/*/templates/*canary*cronjob*.yaml`
- **Chain anchor CronJobs** post head hash to S3 / webhook when configured
- **PDB + HPA** maintain sidecar quorum during rollouts

### Manual (operator)

1. Restore Postgres / Redis connectivity.
2. Clear diagnostic mode: `POST /internal/diagnostic/clear` (admin token).
3. Confirm circuit recovery: successful Redis ping → `record_success`.
4. For ModelGovernor live LLM: set `PROVIDER_MODE=live` + API keys via secret mount.
5. Rollout restart gateway/sidecar if env changed: `kubectl rollout restart deployment/...`

---

## 5. Incident response phases

### Phase 1 — Isolation (automatic)

1. Circuit breaker trips on dependency failures.
2. Traffic continues on local fallback limits (bounded — not unbounded bypass).
3. Diagnostic mode may halt writes if invariants fail — **reads remain** for forensics.
4. Hash chain rows already sealed in Postgres are **unchanged**.

### Phase 2 — Recovery (operator)

```bash
# Offline verification before re-enabling writes
make plug

# Optional live CG verification (Docker)
make compose-smoke-cg

# Per-governor chain verify (example: Cybersecurity Governor)
curl -sf -H 'x-internal-token: $CG_INTERNAL_TOKENS' \
  http://localhost:8121/internal/security/verify-chain

# Clear diagnostic (admin token required)
curl -sf -X POST -H 'x-admin-token: ...' \
  http://localhost:8121/internal/diagnostic/clear
```

### Phase 3 — Attestation

Generate examiner evidence after recovery:

```bash
make cg-examiner-evidence    # Cyber
make fg-examiner-evidence    # Finance (if configured)
```

Reject stub attestations — validators require live probes (`attestation_validate.py`).

---

## 6. Local validation suite

```bash
make plug                                    # portfolio harness
python -m spine_core.port_checks             # port alignment
PYTHONPATH=governor-spine-core pytest governor-spine-core/tests/ -q
pytest -k "circuit or diagnostic or mesh" cybersecurity-governor/tests/ -q
```

---

## Related

- [transactional-kernel-strategy.md](transactional-kernel-strategy.md) — buyer fit + commercial headwinds
- [maturity-ladder.md](maturity-ladder.md) — L4 / L5 / Industry Leading definitions
- [../../docs/institutional-reliability.md](../../docs/institutional-reliability.md) — ModelGovernor failure matrix
