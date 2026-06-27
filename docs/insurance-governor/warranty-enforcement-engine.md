# Warranty Enforcement Engine — Cross-Platform Loss Control Moat

Insurance Governor’s **`crystal_mesh_rules`** runtime is an **automated Warranty Enforcement Engine**. Policy warranties that insurers write into cyber, crime, D&O, and E&O wordings become **impossible to violate at commit time** when the insured deploys two or more platforms on the shared spine.

---

## Insurance framing

| Finance term | Insurance term |
|--------------|----------------|
| Pre-trade risk gate | **Loss control technology** |
| Exposure reservation | **Indemnity spend cap / reserve hold** |
| Settlement | **Governed payout / bind commit** |
| Mesh invariant | **Policy warranty enforcement** |
| Hash-chained ledger | **Attestation spine for underwriting credit** |

**Pitch to insurers:** “We provide an immutable, hash-chained `claim_events` ledger that proves compliance with policy conditions in real time — reducing claims frequency, severity, and defense-cost reserves.”

**Pitch to corporate insureds:** “Deploy two or more wedges on our spine; your insurer can reduce deductibles because cross-platform invariants cryptographically prevent cascading losses.”

---

## Seeded mesh invariants (migration `0007`)

| Parent platform | Parent facet | Blocks child | Insurance warranty enforced |
|-----------------|--------------|--------------|----------------------------|
| `model_risk_freeze` | `freeze_state=FROZEN` | `claim_gate` | No auto-adjudication while claims AI model is out of version |
| `model_risk_freeze` | `freeze_state=FROZEN` | `indemnity_pay_gate` | No indemnity wire while pricing/triage model frozen (E&O / Cyber) |
| `claim_gate` | `gate_decision=REFERRED` | `indemnity_pay_gate` | No payment while SIU referral open (fraud warranty) |
| `underwriting_govern` | `govern_decision=VIOLATION` | `bind_authority` | No bind while fair-lending / bias violation (D&O / regulatory) |
| `reserve_reconcile` | `match_state=DRIFT` | `claim_gate` | No payout while case reserve ≠ reinsurance ledger (solvency / D&O) |
| `reserve_reconcile` | `match_state=DRIFT` | `indemnity_pay_gate` | No indemnity payment on drifted reserves |

Enforcement point: **`POST /commit`** on the child platform (`commit_ledger._check_mesh_block`). Parent crystals remain **non-terminal** while the warranty is breached.

---

## Finance → Insurance platform map

| Finance wedge | Insurance wedge | Port | Loss line |
|---------------|-------------------|------|-----------|
| AlgoFreeze | **ModelRiskFreeze** | 8111 | E&O / Cyber — catastrophic model failure |
| WireMatch | **IndemnityPayGate** | 8110 | Crime / FI Bond — social engineering, fat-finger |
| CreditGovern | **UnderwritingGovern** | 8112 | D&O / Regulatory — fair lending, bias |
| SubledgerSync | **ReserveReconcile** | 8113 | Operational / D&O — reserve misstatement |

---

## Demo: cascading loss prevention

```bash
make ig-stack-up

# 1. Freeze claims model (version drift)
curl -X POST localhost:8111/inference/evaluate \
  -H 'content-type: application/json' \
  -d '{"inference_id":"demo-freeze","runtime_version":"rogue-v9","jurisdiction":"UK"}'
# → 403 MODEL_FROZEN; open crystal with freeze_state=FROZEN

# 2. Attempt governed claim payout — blocked at commit by mesh
curl -X POST localhost:8103/claim/evaluate \
  -H 'content-type: application/json' \
  -d '{"claim_id":"demo-clm","payout_amount":"50000","policy_number":"POL-MOTOR-UK-001"}'
# → crystal created; commit blocked if spine enforces mesh on APPROVED path
```

Run `make ig-spine-test` — includes `test_mesh_warranty.py`.

---

## Underwriting impact (actuarial language)

| Control | Expected impact |
|---------|-----------------|
| ModelRiskFreeze + mesh | ↓ E&O / cyber severity tail; supports **model change management** warranty |
| IndemnityPayGate | ↓ Crime claim frequency; supports **dual authorization / payee verification** warranty |
| UnderwritingGovern + mesh | ↓ D&O defense reserves; **Consumer Duty / ECOA** audit trail |
| ReserveReconcile + mesh | ↓ reserve inadequacy surprises; **Solvency II / NAIC** reporting confidence |

---

## Related

- [insurer-persona-mapping.md](insurer-persona-mapping.md)
- [uk-us-regulatory-framework.md](uk-us-regulatory-framework.md)
- [market-gaps-insurance.md](market-gaps-insurance.md)
