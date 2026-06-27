# CRO Technical Presentation — Claims Leakage Reduction

**Audience:** Chief Risk Officer, Chief Actuary, Head of Claims, Lloyd's / London market syndicate leads  
**Duration:** 45 minutes (+ 15 min Q&A)  
**SKU story:** `IG-PLATFORM-PRODUCTION` — loss-control attestation spine  
**Core promise:** *Prove policy warranties at commit time — stop leakage before indemnity leaves the balance sheet.*

---

## Deck structure (slide-by-slide)

### Section A — The problem (Slides 1–4) · 8 min

| Slide | Title | Content | Visual |
|-------|-------|---------|--------|
| **A1** | Title | *Insurance Governor — Runtime Loss Control for Financial Lines* | Logo + tagline |
| **A2** | Claims leakage today | Leakage = paid loss + ALAE + reserve strengthening that **should not have been authorized** under policy warranties | Funnel: FNOL → adjust → pay → **leak** |
| **A3** | Why controls fail post-hoc | PAS workflows, SIU scores, and MRM dashboards operate **after** reserve commitment | Timeline: breach → days → payment |
| **A4** | CRO question | *"Can you prove the control was active **at the moment of indemnity**?"* | Red box: examiner / Lloyd's / NAIC ask |

**Speaker note:** Frame leakage in actuarial language — frequency (unauthorized claims accepted), severity (over-limit payouts), and reserve volatility (drift before cedent sync).

---

### Section B — Architecture (Slides 5–8) · 10 min

| Slide | Title | Content | Visual |
|-------|-------|---------|--------|
| **B1** | Where we sit | Upstream of payment — downstream of PAS FNOL | Stack diagram from `insurance-governor-production.md` |
| **B2** | Reserve-before-payout | Crystallize → reserve hold → governed commit → payout rail | Sequence: crystal → escrow → event |
| **B3** | Tamper-evident spine | Hash-chained `claim_events` + hourly verify + S3 anchor | Chain of 3 events with `prev_hash` |
| **B4** | Zero-trust platform path | Platform adapters → mTLS → sidecar (not PAS bypass) | Mesh diagram: ClaimGate → sidecar :8101 |

**Proof point:** `GET /internal/claims/verify-chain` returns `valid: true` — live demo or attestation screenshot.

---

### Section C — Leakage controls (Slides 9–16) · 15 min

Map each slide to a **leakage class** and **warranty enforced**:

| Slide | Title | Leakage class | Control | Metric hook |
|-------|-------|---------------|---------|-------------|
| **C1** | Warranty Enforcement Mesh | Cascading loss | Parent crystal blocks child commit | `mesh_block_total` |
| **C2** | ModelRiskFreeze | E&O / Cyber severity tail | No payout while model frozen | ↓ tail severity |
| **C3** | ClaimGate + SIU | Fraud frequency | `REFERRED` blocks IndemnityPayGate | ↓ paid fraud claims |
| **C4** | IndemnityPayGate | Crime / social engineering | Semantic payee verification | ↓ wrongful wire |
| **C5** | ReserveReconcile | Reserve inadequacy | DRIFT blocks payout | ↓ reserve strengthening events |
| **C6** | UnderwritingGovern | D&O / regulatory | Bias violation blocks bind | ↓ defense ALAE |
| **C7** | Policy rules (ClaimGate) | Severity leakage | Limits, deductibles, auto-approve authority | ↓ limit breaches |
| **C8** | ParametricOracle | Cat basis risk | Attestation hash on trigger feed | ↓ disputed parametric pays |

**Mesh table (single reference slide):**

| Parent breach | Blocks | Line |
|---------------|--------|------|
| Model FROZEN | Claim + indemnity pay | E&O / Cyber |
| SIU REFERRED | Indemnity pay | Crime |
| Reserve DRIFT | Claim + indemnity pay | Solvency |
| UW VIOLATION | Bind | D&O |

Source: [warranty-enforcement-engine.md](../insurance-governor/warranty-enforcement-engine.md)

---

### Section D — Quantified impact (Slides 17–19) · 7 min

| Slide | Title | Content |
|-------|-------|---------|
| **D1** | Actuarial framing | Translate controls → **expected loss ratio improvement** (illustrative ranges — buyer actuary validates) |
| **D2** | Illustrative model | See table below |
| **D3** | Deductible / pricing lever | *"Verified runtime controls support deductible reduction and capacity release"* |

**Illustrative impact table (label clearly as model — not guaranteed):**

| Control deployed | Leakage type | Indicative annual saving* | Assumption |
|------------------|--------------|---------------------------|------------|
| SIU block at commit | Fraud paid loss | 0.3–0.8% of net claims | £500M net claims base |
| IndemnityPayGate | Crime wire fraud | £2M–£8M | 4–15 prevented wires |
| ModelRiskFreeze mesh | E&O tail | 5–15% tail reduction | Cyber book |
| ReserveReconcile | Reserve strengthening | 0.5–1.2% reserve volatility | FI lines |

\*Buyer actuary must sign off — use as **discussion model** only in live presentations.

---

### Section E — Evidence & trust (Slides 20–23) · 5 min

| Slide | Title | Content |
|-------|-------|---------|
| **E1** | L4 Gold certification | 35+ automated gates, Helm HA, chaos tier | `make ig-certification-l4-ci` |
| **E2** | Examiner pack | Regulatory export, admin audit hash chain, SOC2 evidence scaffold | `make ig-examiner-evidence` |
| **E3** | Design-partner attestation | Redacted carrier rehearsal (NDA full letter) | `data-room/design-partner-attestation-redacted.md` |
| **E4** | Gap honesty | No named prod carrier yet · ZK = SHA-256 commitment · PAS not replaced | FAQ table |

---

### Section F — Path forward (Slides 24–26) · 5 min

| Slide | Title | Content |
|-------|-------|---------|
| **F1** | 30-day PoC | Scope, success criteria, stub payment rail | Link: [Tier-1 PoC playbook](06-tier1-carrier-poc-playbook.md) |
| **F2** | Packaging | Spine + ClaimGate + wedge · £180K–£320K Yr1 VPC | `IG-PLATFORM-PRODUCTION` |
| **F3** | Ask | Design-partner LOI + staging VPC week · named CRO sponsor | Signature block |

---

## Appendix slides (leave-behind / deep dive)

| ID | Topic | When to use |
|----|-------|-------------|
| **X1** | FNOL vendor matrix (6 adapters) | Integration workshop |
| **X2** | Istio mTLS + platform ingress policy | CISO parallel track |
| **X3** | Postgres idempotency under load | CTO / engineering |
| **X4** | Competitive vs PAS / SIU / MRM | Procurement challenge |
| **X5** | IP licensing summary | Legal / M&A |

---

## Live demo script (12 min embedded in Section C)

Run during **C3** (SIU) and **C1** (mesh):

```bash
make ig-stack-up

# 1. SIU referral path
curl -X POST localhost:8103/claim/evaluate -H 'content-type: application/json' \
  -d '{"claim_id":"cro-demo-1","payout_amount":"250000","policy_number":"POL-HIGH-RISK"}'
# Show REFERRED → indemnity blocked

# 2. Mesh: freeze then block
curl -X POST localhost:8111/inference/evaluate -H 'content-type: application/json' \
  -d '{"inference_id":"cro-freeze","runtime_version":"rogue-v9","jurisdiction":"US"}'
# Attempt payout → mesh block

# 3. Chain verify
curl -s localhost:8101/internal/claims/verify-chain | jq '.valid'
```

---

## CRO-specific Q&A prep

| Question | Answer |
|----------|--------|
| "How is this different from Guidewire rules?" | PAS rules are config-time; IG enforces **cross-system warranties at commit** with hash-chained proof. |
| "Will this slow claims?" | Governed payout p95 target **≤500ms** — pre-execution gate, not batch review. |
| "Lloyd's / syndicate angle?" | Crystal trail + ZkClaimAudit selective disclosure for coverholder audits. |
| "Model risk?" | ModelRiskFreeze ties to MRM inventory — freeze blocks indemnity until version cleared. |
| "What if Redis fails?" | Symmetric degradation — per-pod limits, not unbounded bypass (institutional reliability doc). |

---

## Design notes

- **Color language:** Red = leakage / breach · Green = blocked commit · Blue = attestation / chain
- **Avoid:** "AI magic," full SNARK claims, sports/wagering analogies
- **Lead metric:** *Leakage prevented at commit* (count of `mesh_block` + `BLOCKED` payment statuses)
- **Close:** CRO sponsor signs PoC charter — not full production order

---

## Related

- [Insurance Governor production sheet](insurance-governor-production.md)
- [Capability matrix](../insurance-governor/capability-matrix.md)
- [Tier-1 PoC playbook](06-tier1-carrier-poc-playbook.md)
- [IP licensing framework](05-ip-licensing-framework.md)
