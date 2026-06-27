# Insurance Market Gaps — Loss Control & Attestation Spine

Where P&C, specialty, and financial-lines insurers have weak **runtime** loss control — and how Insurance Governor answers with UK/US standards.

---

## Selection criteria (insurance-specific)

1. **Indemnity spend at stake** — not analytics-only
2. **Policy warranties exist** — but are enforced post-claim, not at runtime
3. **Regulatory examination burden** — FCA, PRA, state DOI, Lloyd's
4. **Cross-line cascading loss** — cyber model failure → wrongful payment → D&O event
5. **Incumbents are policy-admin or SIU point tools** — no unified attestation spine

---

## Tier 1 — Highest insurer desirability

### 1. Claims AI / auto-adjudication (E&O / Cyber)

**Gap:** Model version drift, ungoverned auto-approve above authority, no immutable inference trail.

**Answer:** ModelRiskFreeze + ClaimGate mesh + hash-chained `claim_events`.

**UK:** PRA SS1/23, FCA Consumer Duty  
**US:** NAIC model governance expectations, state DOI AI bulletins

**Buyer:** CRO, Chief Actuary, InsurTech platform lead

---

### 2. Crime / social engineering indemnity (FI bonds)

**Gap:** Payee verification after the fact; crime policies pay on “reasonable security procedures” breach.

**Answer:** IndemnityPayGate semantic payee gate + mesh blocks during SIU / model freeze.

**UK:** FCA PS21/3 (operational resilience), APP fraud guidance  
**US:** FBI IC3 trends, crime policy social engineering endorsements

**Buyer:** Head of Financial Crime UW, Claims Director

---

### 3. Underwriting fairness (D&O / regulatory)

**Gap:** Quarterly bias testing; no per-bind compliance crystal.

**Answer:** UnderwritingGovern + mesh blocks BindAuthority on `VIOLATION`.

**UK:** Equality Act, Consumer Duty outcomes  
**US:** ECOA adverse action, state unfair discrimination statutes

**Buyer:** General Counsel, D&O underwriter

---

### 4. Reserve / reinsurance drift (operational / D&O)

**Gap:** Case reserve ≠ reinsurance bordereaux; discovered at quarter close.

**Answer:** ReserveReconcile + mesh blocks payout on `DRIFT`.

**UK:** Solvency II technical provisions  
**US:** Statutory accounting, Schedule F

**Buyer:** Chief Actuary, CFO

---

## Tier 2 — Strong follow-on

| Gap | Wedge | Line |
|-----|-------|------|
| Parametric cat trigger fraud | ParametricOracle + oracle attestation | Property cat |
| Property damage dispute | SpatialTwin LiDAR hash | Property |
| EV fleet battery events | BatteryLiability | Auto / fleet |
| Subrogation leakage | SubrogationGraph | Casualty |

---

## Competitive landscape (honest)

| Incumbent | Strength | IG gap filled |
|-----------|----------|---------------|
| Guidewire / Duck Creek | Policy admin, FNOL | No runtime warranty mesh |
| FRISS / Shift | SIU fraud scores | No payment-block mesh with model freeze |
| ModelOp / Monitaur | Model validation lifecycle | No reserve-before-payout enforcement |
| GRC (Archer, ServiceNow) | Policy documentation | No sub-second commit-time block |

**Positioning:** Runtime **loss control attestation spine** — not replacing PAS or MRM, but enforcing warranties in production with examiner-grade chain.

---

## Wedge recommendation for insurance GTM

**Lead with:** ModelRiskFreeze + IndemnityPayGate + mesh demo (E&O/Cyber + Crime story).

**Expand to:** ClaimGate FNOL + ReserveReconcile for P&C carrier design partner.

**UK entry:** `crime-indemnity-uk`, `POL-MOTOR-UK-001`, Consumer Duty narrative.

**US entry:** Guidewire FNOL webhook + NAIC chain verify narrative.
