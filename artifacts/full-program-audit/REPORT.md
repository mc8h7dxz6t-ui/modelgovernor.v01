# Full Program Test & Audit Report

**Generated:** 2026-06-29T23:50:56Z  
**Git SHA:** `258ff0fd79087b54171abe0c94736711399d91ba` (+ CI fix `22817f8`)  
**Harness:** `scripts/run-full-program-audit.sh`  
**Result:** **19/19 PASS** (0 failed, 0 skipped)

---

## Executive summary

A rigorous cross-platform test and static conformance audit was executed across all four governors and the shared kernel (`governor-spine-core`). All automated gates passed after correcting a **PYTHONPATH regression** introduced when H1/M1 moved shared modules into `spine_core` — Makefiles now consistently include `governor-spine-core` on the test path.

| Layer | Verdict | Score |
|-------|---------|-------|
| **Shared kernel** | PASS — K1, K3, H1, K4, M1 conformance green | **9.0/10** (code) |
| **ModelGovernor** | PASS — L4 CI + integration hardening | **7.5/10** |
| **Finance Governor** | PASS — 133 unit + 32 L4 CI | **7.0/10** |
| **Insurance Governor** | PASS — 143 unit + 47 L4 CI | **8.0/10** |
| **Cybersecurity Governor** | PASS — 95 unit + 43 L4 CI + property chain | **8.5/10** |
| **Portfolio (L5 plug)** | PASS — `make plug` + `portfolio_self_check.json` | **7.5/10** |

**Portfolio IL 9/10 is not claimed** — Phase C external evidence (design-partner letters) remains a human gate per governor.

---

## 1. Kernel static conformance (6/6 PASS)

| Gate | Module | Result |
|------|--------|--------|
| **K1** | `spine_core.ledger_registry` — seal fn + verify fn per governor | PASS |
| **K3** | `spine_core.sweep_seal` — reconciler sweep uses sealed append | PASS |
| **H1** | `spine_core.append_lock` — advisory lock on all append paths | PASS |
| **K4** | `spine_core.retention_cronjob` — Helm retention CronJob templates | PASS |
| **M1** | `spine_core.m1_conformance` — checkpoint shims, mesh, metadata | PASS |
| **Ports** | `spine_core.port_checks` — Docker/Helm port alignment | PASS |

---

## 2. Spine-core unit tests (25 PASS)

```
PYTHONPATH=governor-spine-core python3 -m pytest governor-spine-core/tests/ -q
25 passed
```

Covers: config contract, ledger conformance, sweep seal, append lock, retention runner/cronjob, M1 conformance, verify HTTP client, port checks.

---

## 3. Per-governor test matrix

### ModelGovernor (MG)

| Suite | Tests | Result |
|-------|-------|--------|
| Integration hardening + seal fail-closed | 8 | PASS |
| L4 certification CI (property ledger, finance_ops_finals, leader election, helm) | 11 passed, 2 skipped | PASS |

**Notes:** Property-based ledger tests and finance_ops_finals require `PYTHONPATH=governor-spine-core:.` (now wired in Makefile).

### Finance Governor (FG)

| Suite | Tests | Result |
|-------|-------|--------|
| `fg-spine-test` (unit, excl. integration) | 133 passed, 2 skipped | PASS |
| `fg-certification-l4-ci` | 32 passed | PASS |

**Coverage:** horizon sweeper, reconciler leader, commit invariants, incremental chain verify, seal fail-closed, L4 Helm enterprise.

### Insurance Governor (IG)

| Suite | Tests | Result |
|-------|-------|--------|
| `ig-spine-test` (unit, excl. chaos/load/integration) | 143 passed, 9 skipped | PASS |
| `ig-certification-l4-ci` | 47 passed | PASS |

**Coverage:** FNOL sandbox integration, claim seal fail-closed, spatial/subro HTTP wedges, platform registry.

### Cybersecurity Governor (CG)

| Suite | Tests | Result |
|-------|-------|--------|
| `cg-spine-test` | 95 passed, 8 skipped | PASS |
| `cg-certification-l4-ci` | 43 passed | PASS |
| `cg-property-test` (security chain property) | PASS | PASS |

---

## 4. Portfolio L5 self-check (`make plug`)

| Step | Result |
|------|--------|
| Canonical tree footprint | PASS |
| Port alignment | PASS |
| Spine-core contract tests | 25 PASS |
| CG spine test matrix | 95 PASS |
| FG spine test matrix | 133 PASS |
| IG spine test matrix | 143 PASS |
| MG integration suite | PASS |
| Helm render (CG + MG) | PASS |
| `portfolio_self_check.json` artifact | PASS |

Artifact fields: `k1_ledger_conformance`, `k3_sweep_seal`, `k4_retention_cronjob`, `h1_append_advisory_lock`, `m1_spine_consolidation` — all **shipped**.

---

## 5. Helm / ops verification

| Check | Result |
|-------|--------|
| MG `ledger-retention` CronJob in helm template | PASS |
| FG `decision-retention` CronJob in helm template | PASS |

---

## 6. Findings from this audit

### Fixed during audit (P0)

| ID | Finding | Fix |
|----|---------|-----|
| **CI-1** | Makefiles lacked `governor-spine-core` on PYTHONPATH after H1/M1 | Updated MG root Makefile, `run-salvage-verification.sh`, FG/IG/CG Makefiles |
| **CI-2** | `make plug` failed on CG/FG/IG spine tests | Resolved by CI-1 |

### Not run in this harness (requires Docker / live stack)

| Gate | Reason |
|------|--------|
| `compose-smoke-mg/fg/ig/cg` | Requires Docker compose live stack |
| `*-pilot-attestation` | Requires running sidecar + gateway |
| FG Postgres integration (`fg-integration-test`) | Requires Docker test DB on :5434 |
| IG/CG chaos (Toxiproxy) | Requires `docker-compose.chaos.yml` |
| IG/CG Postgres concurrent append | Requires `POSTGRES_TEST_URL` |
| `demo-gold` / `demo-gold-reliability` | Full MG demo stack |

These are **Tier 3–4 live proof** gates per the maturity ladder — not failures, but out of scope for this offline CI harness.

### Known low-priority warnings (non-blocking)

- Python 3.12 `datetime` adapter deprecation in SQLAlite tests (SQLAlchemy)
- Pydantic `model_` protected namespace warnings in platform tests
- websockets/uvicorn deprecation in FG inference rail test

---

## 7. IL rubric status (honest)

| # | Dimension | MG | FG | IG | CG |
|---|-----------|----|----|----|-----|
| 1 | L4 engineering (CI green) | ✅ | ✅ | ✅ | ✅ |
| 2 | L5 self-check (`make plug`) | ✅ | ✅ | ✅ | ✅ |
| 3 | Live stack proof (compose-smoke) | ⏳ Docker | ⏳ Docker | ⏳ Docker | ⏳ Docker |
| 4 | Hero wedge depth | demo-gold | wire/algofreeze | ClaimGate | EgressGovern |
| 5 | External evidence (Phase C) | ⏳ | ⏳ | ⏳ | ⏳ |

**Kernel code:** 9.0/10 — all K1–K4 + H1 + M1 shipped and verified.  
**Portfolio:** 7.5/10 — no governor has row 5 (external evidence).

---

## 8. Reproduce

```bash
# Full head-of-engineering gate (19 checks, ~45s)
./scripts/run-full-program-audit.sh

# Individual governor L4 CI
make mg-certification-l4-ci
make -C finance-governor fg-certification-l4-ci
make -C insurance-governor ig-certification-l4-ci
make -C cybersecurity-governor cg-certification-l4-ci

# Portfolio L5 plug
make plug
```

Artifacts: `artifacts/full-program-audit/summary.json`, `artifacts/portfolio_self_check.json`

---

## 9. Recommendation

1. **Merge PR #59** with CI-1 PYTHONPATH fix — unblocks all Makefile-based gates.
2. **Add `run-full-program-audit.sh` to CI** as a portfolio gate job (parallel to `make plug`).
3. **Schedule Docker-tier gates** (compose-smoke ×4) in a nightly or pre-release pipeline.
4. **Phase C** remains the only path to portfolio 9/10 — engineering kernel work is complete.
