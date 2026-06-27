# Governor Maturity Ladder — Robust, Reliable, Honest

This document defines certification language used across ModelGovernor, Finance Governor, Insurance Governor, and Cybersecurity Governor.

## Principles

1. **Robust** = survives dependency failure without silent money/security state corruption.
2. **Reliable** = proven by automated gates (pytest, chaos, Helm render) — not marketing copy.
3. **Industry Leading** = reserved for **kernel architecture grade** when external evidence exists — not self-awarded from CI alone.

---

## Levels

### L1 — Platform Ready

- Standalone `/healthz` + `/readyz`
- Tier 1 unit tests
- Facet schema declared in platform manifest

### L2 — Institutional

- Diagnostic mode compatible (writes halt, reads continue)
- Invariant counters on governed paths
- Idempotent mutations (replay-safe crystallize/reserve)

### L3 — Institutional++

- Spine adapter integration (`SpineAdapter` / platform SDK)
- Postgres integration tests (Tier 2)
- Platform registry row + conformance target

### L4 — Gold Enterprise *(robust baseline for sale)*

| Gate | Command / artifact |
|------|-------------------|
| Spine + platform pytest | `make *-spine-test` |
| Postgres vigorous | Tier 2 CI job |
| Load smoke | Tier 3 CI job |
| Toxiproxy chaos | Tier 4 CI job |
| Helm enterprise render | `make *-helm-enterprise` |
| L4 certification aggregator | `make *-certification-l4-ci` |

**L4 Gold means:** the deploy kit and test pyramid are **enterprise-grade in CI**. It does **not** mean Fortune 500 production attestation without buyer wiring.

### L5 — Institutional Self-Check Certified *(portfolio reliability harness)*

| Requirement | Proof |
|-------------|-------|
| Portfolio harness | `make plug` |
| Port / ledger contract | `python -m spine_core.port_checks` |
| Spine-core unit tests | `pytest governor-spine-core/tests/` |
| Cross-governor Helm smoke | plug Step 7 |

**L5 (repo) means:** offline institutional self-check across governors. See `scripts/run-salvage-verification.sh`.

Per-governor `certification/program.yaml` may list additional L5 items (Istio, live rails) as **buyer VPC overlays** — those are aspirational gates, not implied by `make plug` alone.

### IL — Industry Leading Gold Standard *(external claim only)*

Use **only** when all of the following are true:

| Criterion | Example evidence |
|-----------|------------------|
| L4 + L5 gates green on release branch | CI + `make plug` |
| Live stack attestation in customer or reference VPC | `make cg-pilot-attestation`, `make compose-smoke-cg` |
| External or design-partner attestation artifact | Examiner pack with `pack_sha256`, signed letter |
| No stub probes in published attestation | `attestation_validate.py` rejects `probes_note` stubs |

**Industry Leading** describes the **transactional kernel** (crystallize → seal → commit → prove) — not thin wedge SKUs or integration scaffolds.

---

## What we do not certify

| Claim | Status |
|-------|--------|
| Lamport logical clocks | **Not implemented** — use hash-chained `prev_hash` replay |
| Global `InstitutionalModeController` singleton | **Not implemented** — use per-governor circuit breaker + `mode_contract.py` |
| `kubectl patch` failover on `curl openai.com` | **Rejected** — not production DR |
| Okta / Zscaler / BlackLine replacement | **Not positioned** — complement via wedges |

---

## Governor-specific program files

| Governor | Program manifest |
|----------|-------------------|
| Finance | `finance-governor/certification/program.yaml` |
| Insurance | `insurance-governor/certification/program.yaml` |
| Cyber | `cybersecurity-governor/certification/program.yaml` |
| ModelGovernor | `docs/capability-matrix.md` + root CI tiers |
