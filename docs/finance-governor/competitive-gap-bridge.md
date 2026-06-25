# Competitive Gap Bridge — Finance Governor

How each platform closes the gap vs incumbents, with **testable** institutional++ proof.

## Summary

| Platform | Incumbent gap | Our bridge | Proof |
|----------|---------------|------------|-------|
| **AlgoFreeze** | Exchange kill switches: blunt, not version/feed-aware | CI/CD deploy SHA registry + feed heartbeat + zero egress invariant | `make algofreeze-demo`, `frozen_egress_attempt_total` |
| **WireMatch** | Payment hubs: schema yes, semantic intent weak | Decimal-only pre-rail gate + ISO 20022 intent extraction | `wire_sent_below_threshold_total = 0`, `/wire/evaluate-iso20022` |
| **SubledgerSync** | BlackLine/Duco: batch month-end, no FX hash at clear | Real-time IC pairing with immutable FX snapshot hash | `fx_snapshot_hash` on every match |
| **AssetLedger** | SAP FA / CCH: reporting not runtime control | Daily depreciation with pinned `reg_table_version` | `negative_book_value_total = 0` |
| **CreditGovern** | ValidMind/Fiddler: docs/monitoring, not reserve-before-score | Exposure reserve → score → settle with model version lock | `model_version_mismatch_total`, reserve path |
| **Spine mesh** | K8s circuit breakers: no trading semantics | No wire/credit while algo desk FROZEN | `crystal_mesh_block_total` |

---

## AlgoFreeze vs exchange kill switches & EMS

**Their gap:** Exchange halts and EMS throttles are not tied to **approved deploy SHA** or **feed packet continuity**.

**Our bridge:**
- `DeployRegistry` — CI/CD pipeline registers approved SHA (`POST /admin/deploy-registry`)
- `FeedHeartbeat` — sub-second degradation detection
- `OrderGate` — hard block when `FROZEN`; `frozen_egress_attempt_total` must stay 0
- Append-only freeze event chain (`/internal/events/recent`)

**Demo:** `make algofreeze-demo` — wrong SHA → 403 → status `FROZEN` → subsequent orders blocked.

---

## WireMatch vs payment hubs & SWIFT tooling

**Their gap:** Finastra/FIS validate schema; SWIFT checks format; Pelican screens AML — none do **semantic beneficiary intent** before rail send.

**Our bridge:**
- Token-overlap semantic scorer + Decimal amount anomaly (Citigroup-class fat-finger)
- `iso20022_adapter.py` — extract intent from pacs.008 stub
- `execution_gate.py` — evaluate → send with idempotency duplicate block
- Crystal mesh: wire HELD if algo desk frozen

**Demo:** `make wirematch-demo` — $900M wire HELD on amount anomaly.

---

## SubledgerSync vs BlackLine & Duco

**Their gap:** Close management and record match at month-end; FX drift found late.

**Our bridge:**
- `capture_fx_snapshot()` — rate + timestamp → SHA-256 hash at match time
- `canonical_txn_hash()` — cross-entity pairing key
- `MatchEngine` — tolerance in bps, orphan sweep → `ic_orphan_detected_total`

**Demo:** `make subledger-demo` — mirrored UK/US pair matched with FX hash.

---

## AssetLedger vs SAP FA & CCH Tagetik

**Their gap:** Heavy ERP modules; tax tools report, don't **control** runtime write-downs.

**Our bridge:**
- `RegTableSync` pins HMRC/IRS table version per asset
- `DepreciationEngine` — one charge per (asset, period), book value clamp
- Append-only depreciation events

**Demo:** `make assetledger-demo` — charge with `hmrc-2026-q1` pinned.

---

## CreditGovern vs ValidMind, Arthur, Bedrock guardrails

**Their gap:** MRM lifecycle docs and post-inference monitoring; no **sub-second reserve-before-score** with exposure escrow.

**Our bridge:**
- `ExposureLedger.reserve()` before mock rail invocation
- `PolicyRegistry` blocks unregistered model versions
- High-risk → STRANDED (not silent approve/deny)
- Above auto-approve threshold → APPROVAL_REQUIRED

**Demo:** `make creditgovern-demo` — governed decision with reserve path.

---

## Cross-platform mesh (institutional++ spine edge)

**Their gap:** Infra circuit breakers lack trading semantics.

**Our bridge:** `MeshGuard` propagates AlgoFreeze `FROZEN` → blocks WireMatch send and CreditGovern score.

**Demo:** `make fg-mesh-demo` — wire HELD with `MESH_BLOCK` while desk frozen.

---

## Certification

```bash
cd finance-governor && make fg-certification
# → artifacts/reliability/finance-governor/latest_certification.json
```

Runs full test pyramid (Tier 1) across all five platforms and records gap-bridge checklist.

**Target levels:** L2 Institutional (current) → L4 Gold with Postgres chaos + K8s HA (roadmap Phase 4).

---

## ACV positioning (unchanged)

| Platform | List ACV |
|----------|----------|
| AlgoFreeze | $150K–$400K/yr |
| WireMatch | $200K–$500K/yr |
| SubledgerSync | $150K–$350K/yr |
| AssetLedger | $100K–$250K/yr |
| CreditGovern | $250K–$600K/yr |
| Full FG bundle | $1M–$2.5M/yr |

Sell as **complement** to incumbents (EMS, BlackLine, ValidMind) — we enforce pre-execution what they document or reconcile post-hoc.
