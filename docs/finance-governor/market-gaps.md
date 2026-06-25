# Finance Deep Dive — Underserved Areas

Where institutional finance has weak tooling and Finance Governor can answer common problems with ModelGovernor-grade reliability.

## Selection criteria

We prioritize domains where:

1. **Decisions have financial or regulatory consequence** — not just analytics
2. **Ambiguous outcomes are common** — timeouts, partial data, disputed results
3. **Pre-action control matters** — blocking is cheaper than remediating
4. **Audit burden is high** — examiners, model risk, fair lending, AML
5. **Incumbents are fragmented** — MRM platforms + cloud ML + spreadsheets, no unified control plane

---

## Tier 1 — Highest wedge potential

### 1. AI credit and underwriting decisions

**Problem:** Banks deploy ML for credit scoring, limit setting, and early warning. Regulators (FCA, OCC, CFPB, EBA) expect explainability, bias testing, and ongoing monitoring. Today: model in production, governance in Confluence, evidence assembled manually for exams.

**Common pain:**
- No pre-dispatch exposure cap (model can approve unlimited notional before human review)
- Version drift: production model ≠ registered model
- Settlement ambiguity: application timeout — was credit pulled? Decision unknown.
- Fair lending: demographic parity checks happen quarterly, not per decision

**Finance Governor answer:**
- Reserve exposure budget per application/desk before inference
- Policy registry: allowed model versions, score bands, max auto-approve notional
- Settle with authoritative outcome + feature attribution snapshot
- Stranded holds for provider timeouts pending manual adjudication
- Append-only decision ledger for SR 11-7 / EU AI Act high-risk evidence

**Buyer:** CRO, Model Risk, Consumer Lending CTO

---

### 2. Fraud and AML screening (AI-augmented)

**Problem:** Transaction monitoring and KYC use rules + ML ensembles. False positive fatigue and alert backlog cost billions. AI adds velocity but regulators demand traceability on alert disposition.

**Common pain:**
- Alert fired but no immutable record of which model version, features, threshold
- Analyst override not linked to original inference reservation
- Batch vs real-time scoring inconsistency
- Sanctions screening timeout → unknown compliance state

**Finance Governor answer:**
- Reserve-before-screen: hold transaction in `PENDING_SCREEN` until settle
- Multi-rail attempts (primary vendor, fallback rules engine) under one logical operation
- Analyst disposition as settlement with identity match to original reserve
- Regulatory export: alert lineage from reserve → inference → disposition

**Buyer:** Head of Financial Crime, AML Operations, RegTech

---

### 3. Algorithmic trading and execution AI guardrails

**Problem:** Desks use ML for signal generation, execution algos, and smart order routing. Pre-trade risk exists for orders; **inference spend and model-driven intent** often bypass unified controls.

**Common pain:**
- Agent loops re-querying models in volatile markets (cost + risk)
- No per-strategy inference budget or latency SLO enforcement
- Model output used after stale reservation expired
- P&L attribution to model version is manual

**Finance Governor answer:**
- Per-strategy exposure and inference budgets (adapt `trace_budget_state`)
- Circuit breaker on model rail failures with local fallback
- Drift lockout when realized slippage exceeds reserved tolerance
- Attribution by desk / book / strategy / model version

**Buyer:** Head of Electronic Trading, Market Risk, Quant Platform

---

### 4. Insurance claims and pricing AI

**Problem:** Claims triage and dynamic pricing models affect reserves and solvency. Actuarial and regulatory scrutiny on model change management is intense; runtime governance is thin.

**Common pain:**
- Auto-adjudication above threshold without approval gate
- Pricing model A/B tests not reconciled to bound policies
- Claim reserve impact not reserved before model recommendation

**Finance Governor answer:**
- Manual approval gate for claims above reserve threshold (existing `guardrail_incidents` pattern)
- Policy-bound pricing model allowlist per product line
- Settlement ties recommendation to claim ID with immutable feature store hash

**Buyer:** Chief Actuary, Claims Operations, InsurTech platform leads

---

## Tier 2 — Strong follow-on

### 5. Wealth and robo-advisory suitability

Suitability rules + ML portfolio recommendations. MiFID II / Reg BI require best-interest documentation per recommendation. Gap: no reserve-before-recommend for concentration or risk budget breaches.

### 6. Treasury and cash forecasting AI

Working capital models drive funding decisions. Gap: no auditable link between forecast model version and treasury action; reconciliation when actuals diverge from reserved liquidity assumption.

### 7. Regulatory reporting and NLP extraction

LLMs extract data for FINREP, CCAR narratives, ESG disclosures. Gap: hallucination risk with no pre-dispatch policy on source documents, no settlement against authoritative filing values.

### 8. Internal finance ops (close, reconciliation, anomaly detection)

Close automation AI flags journal anomalies. Gap: no segregation-of-duties gate before auto-posting; no ledger-backed proof that AI suggestion was reviewed and settled.

---

## Tier 3 — Crowded or lower differentiation

| Area | Why deprioritize |
|------|------------------|
| Generic BI / forecasting dashboards | Commoditized; weak regulatory hook |
| Chatbots for customer service | Dominated by CCaaS vendors; lower institutional++ bar |
| Basic expense OCR | Ramp, Brex, SAP already own workflow |
| Payment routing optimization | Strong incumbents (Stripe, Adyen treasury) |

---

## Wedge recommendation

**Start with AI Credit Decision Governance** (Tier 1 #1):

| Factor | Rationale |
|--------|-----------|
| Regulatory heat | EU AI Act high-risk, FCA AI guidance, CFPB adverse action |
| Spine fit | Reserve/settle maps cleanly to exposure reservation per application |
| Demo clarity | Approve/deny/timeout story is legible to non-quants in 5 minutes |
| Expansion path | Fraud (#2) shares same escrow + screening rail pattern |
| ModelGovernor reuse | `budget_scope_state`, `guardrail_incidents`, `execution_lineage` port directly |

Second wedge: **Fraud/AML screening** — same architecture, different policy registry and settlement semantics.

---

## Competitive landscape (honest)

| Competitor type | Strength | Gap Finance Governor fills |
|-----------------|----------|---------------------------|
| Model risk platforms (SR 11-7) | Validation lifecycle | No runtime reserve-before-decision |
| Feature stores (Tecton, Feast) | Training/serving features | No financial escrow or settlement |
| MLOps (MLflow, W&B) | Experiment tracking | No institutional ledger or reconciler |
| GRC suites (Archer, ServiceNow) | Policy documentation | No sub-second enforcement at inference |
| Cloud AI guardrails (Bedrock, Azure) | Content safety | Not finance-specific; no examiner-grade chain |

**Positioning:** Runtime financial AI control plane — not replacing MRM validation, but enforcing it in production with the same rigor as payment rails.
