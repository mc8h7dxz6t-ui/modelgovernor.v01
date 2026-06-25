# Finance Governor — Inaugural Program

**CreditGovern** — governed credit inference. One of five standalone platforms; runs alone or on the shared spine.

See also: [AlgoFreeze](../algofreeze/), [WireMatch](../wire_match/), [SubledgerSync](../subledger_sync/), [AssetLedger](../asset_depreciation/).

## Deployment modes

| Mode | Dependencies |
|------|--------------|
| **Standalone** | Credit gate + mock rail + local `platform_events` |
| **Spine-connected** | + Finance Governor sidecar for unified audit + regulatory export |

## Scope

Governed credit inference with institutional++ controls:

- Reserve exposure before credit model invocation
- Instrument policy enforcement (model version, jurisdiction, risk tier)
- Settlement with decision outcome + explainability artifact binding
- Exposure drift detection and desk lockout
- Reconciler expiry/stranded holds for ambiguous inference
- Session-wide regulatory invariant audit (`regulatory_ops.py`)
- Multi-dimensional attribution (tenant, desk, application, model version)

## Out of scope (this program)

- Full loan origination system (LOS)
- Credit bureau integration (simulate via mock rail)
- Document OCR / income verification
- Funding / disbursement rails

Finance Governor is the **governance control plane** around credit inference, not the origination platform.

---

## User stories

### US-1: Auto-approve within policy

> As a consumer lending platform, I want credit models to auto-approve only when exposure is within desk budget and below auto-approve threshold, so we never exceed risk appetite without human review.

**Acceptance:**
- Reserve debits desk exposure budget atomically
- Approval above `max_auto_approve_amount` returns 403 + `APPROVAL_REQUIRED` incident
- Settlement binds `explanation_artifact_id`

### US-2: Ambiguous inference handling

> As a compliance officer, I want timeout outcomes stranded (not silently approved or denied), so we never have unknown compliance state.

**Acceptance:**
- `PROVIDER_TIMEOUT` → reconciler sets `STRANDED`
- High-risk policies never auto-expire to refund
- `MANUAL_ADJUDICATION` event on officer resolution

### US-3: Examiner audit trail

> As model risk management, I need an immutable decision chain per application, so SR 11-7 and EU AI Act evidence is production-retrievable.

**Acceptance:**
- `decision_events` append-only with hash chain
- `GET /internal/decisions/verify-chain` returns valid
- `GET /internal/lineage/{idempotency_key}` returns feature snapshot hash

### US-4: Model version integrity

> As a model owner, I want production inference blocked if model version doesn't match registered policy, so shadow models cannot run.

**Acceptance:**
- Reserve checks `model_version_id` against `instrument_policy_registry`
- Mismatch increments `model_version_mismatch_total` and blocks

---

## APIs (target)

### Governed lifecycle

```
POST /governed/decision
  Body: { instrument_type, application_id, exposure_amount, feature_snapshot_hash, ... }
  → reserve → inference → settle
```

### Internal diligence (x-internal-token)

```
GET /internal/account/{account_id}
GET /internal/decision/{idempotency_key}
GET /internal/exposure/{scope_key}
GET /internal/attribution/summary?dimension=desk|tenant|model_version
GET /internal/guardrail/incidents
GET /internal/lineage/{idempotency_key}
GET /internal/decisions/verify-chain
GET /internal/regulatory/export?application_id=...
```

---

## Test plan

```bash
# Program tests (when scaffold lands)
pytest -q tests/programs/finance_governor/

# Expected test modules:
# - test_credit_reserve_settle_lifecycle.py
# - test_exposure_cap_enforcement.py
# - test_high_risk_stranded_semantics.py
# - test_model_version_policy.py
# - test_manual_approval_gate.py
# - test_regulatory_ops_invariants.py
# - test_attribution_summary.py
```

---

## Demo script (fg-demo-gold target)

| Step | Action | Proof |
|------|--------|-------|
| 1 | Boot stack | `make fg-demo-up` healthy |
| 2 | Credit approve (in policy) | SETTLED, exposure debited |
| 3 | Credit deny | SETTLED deny + explanation |
| 4 | Above auto-approve threshold | 403 APPROVAL_REQUIRED |
| 5 | Desk exposure cap exceeded | 409 insufficient exposure |
| 6 | Inference timeout | STRANDED after reconciler |
| 7 | Inspect decision ledger | `make fg-demo-ledger` |
| 8 | Inspect events | append-only trail |
| 9 | Drift enforcement | lock desk on overrun |
| 10 | Verify hash chain | verify-chain API |
| 11 | Regulatory ops audit | reconciler post-sweep clean |

---

## Metrics

| Counter | Meaning |
|---------|---------|
| `exposure_reserve_denied_total` | Insufficient desk budget |
| `auto_approve_blocked_total` | Above threshold, needs approval |
| `model_version_mismatch_total` | Unregistered model blocked |
| `bias_cohort_divergence_total` | Cohort threshold breach |
| `decision_stranded_total` | Ambiguous outcomes |
| `exposure_drift_enforced_total` | Desk lock from drift |
| `regulatory_audit_violation_total` | Invariant probe failure |

---

## ModelGovernor files to port

| Source | Target |
|--------|--------|
| `sidecar/app/ledger.py` | `decision_ledger.py` |
| `sidecar/app/finance_ops.py` | `regulatory_ops.py` |
| `sidecar/app/attribution.py` | `attribution.py` (+ desk/book) |
| `sidecar/app/ledger_seal.py` | `decision_seal.py` |
| `gateway/app/governance.py` | `governance.py` |
| `reconciler/app/sweeper.py` | `sweeper.py` (+ high-risk rules) |
| `programs/finance_ops_finals/` | This program's test structure |

---

## Docs

- `docs/finance-governor/README.md` — platform vision
- `docs/finance-governor/market-gaps.md` — why credit first
- `docs/finance-governor/governance-framework.md` — regulatory mapping
- `docs/finance-governor/architecture.md` — spine design
- `docs/finance-governor/domain-model.md` — schema
- `docs/finance-governor/roadmap.md` — phased delivery
