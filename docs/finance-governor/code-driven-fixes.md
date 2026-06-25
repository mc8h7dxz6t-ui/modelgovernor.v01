# Code-Driven Finance Fixes — Deep Dive

Four high-cost finance failure modes with original, codebase-first solutions. Each maps to a **standalone platform** that optionally connects to the Finance Governor spine.

---

## Cost taxonomy

| Failure class | Annual / incident cost | Root cause |
|---------------|------------------------|------------|
| Runaway algorithm | $440M in 45 minutes (Knight Capital, 2012) | Wrong code version + no kill switch |
| Wire reference error | $900M sent vs $7.8M intended (Citigroup, 2020) | Unstructured text, no pre-send semantic gate |
| Intercompany drift | Millions in audit fees + tax inefficiency | FX timing, manual reconciliation lag |
| Stale asset books | Tax overpayment, regulatory misstatement | Manual depreciation, year-end batch only |
| Human data-entry | Billions aggregate | No type-safety, no pre-execution validation |
| Version-control gaps | Firm-ending in minutes | Deploy ≠ registered production version |

---

## 1. AlgoFreeze — Dynamic Network Freeze for Live Algo Systems

### The problem

Trading algorithms depend on split-second math across market variables, latency, and feed integrity. If a data source misreports, or a server runs the wrong code version, an algo can execute millions of unintended trades in minutes.

**Reference incident:** Knight Capital — ~$440M loss in ~45 minutes from dormant code accidentally deployed to production servers.

### The cost

Hundreds of millions in minutes. Entire firm viability at risk.

### The code fix — AlgoFreeze platform

A **heartbeat proxy** that sits in front of algo order egress:

```
Market feeds ──► AlgoFreeze Proxy ──► Exchange / EMS
                      │
                      ├── version registry check (deployed SHA == approved SHA)
                      ├── feed heartbeat (Bloomberg/Refinitiv packet cadence)
                      ├── circuit breaker (N missed heartbeats → FREEZE)
                      └── optional: spine reserve before order batch
```

**Core components:**

| Module | Responsibility |
|--------|----------------|
| `version_guard.py` | Compare runtime binary/config hash vs `approved_version_registry` |
| `feed_heartbeat.py` | Async monitor on data feed sockets; track packet inter-arrival |
| `freeze_controller.py` | Atomic state: `ACTIVE` → `DEGRADED` → `FROZEN` |
| `order_gate.py` | Block all egress when `FROZEN`; append `FREEZE_ENFORCED` event |

**Standalone deploy:** Single proxy service + Redis for freeze flag + Postgres for event log.

**Spine-connected:** Each order batch `reserve` notional exposure; freeze triggers `strand` on in-flight batches; examiner sees version + feed state at freeze time.

```python
# Conceptual freeze trigger
if feed.missed_packets >= policy.max_missed_packets:
    freeze_controller.freeze(
        reason="FEED_DEGRADED",
        metadata={"feed": "bloomberg", "gap_ms": gap, "version_sha": runtime_sha},
    )
    circuit_breaker.open_all_rails()
```

**Invariants:**
- No orders egress in `FROZEN` state
- Version mismatch → immediate freeze (configurable: freeze vs alert)
- Freeze events append-only, never deleted

Program: [`programs/algofreeze/`](../../programs/algofreeze/)

---

## 2. WireMatch — Semantic Matching for Cross-Border Payments

### The problem

Legacy banking uses unstructured, varied text fields for wires. Wrong reference, transposed decimal, or beneficiary name mismatch sends money to the wrong party. Recovery is partial or impossible.

**Reference incident:** Citigroup — ~$900M wired to Revlon lenders vs ~$7.8M intended (2020); much never recovered.

### The cost

Billions annually in misrouted wires, manual compliance reconciliation, litigation.

### The code fix — WireMatch platform

**NLP semantic matching + strict type-safety** gate before wire execution:

```
Wire request ──► WireMatch Gate ──► Payment rail
                      │
                      ├── schema validation (ISO 20022 / proprietary normalized)
                      ├── amount type-safety (Decimal, currency quantum)
                      ├── beneficiary semantic match (embedding + rules)
                      ├── reference field anomaly detection
                      └── halt + human review on score < threshold
```

**Core components:**

| Module | Responsibility |
|--------|----------------|
| `wire_schema.py` | Pydantic models — no raw dicts, no float amounts |
| `semantic_matcher.py` | Compare beneficiary name, reference, account metadata vs golden record |
| `anomaly_scorer.py` | Flag decimal transposition, amount order-of-magnitude mismatch |
| `execution_gate.py` | `APPROVED` / `HELD` / `REJECTED` with immutable reason |

**Type-safety rules:**
- All amounts: `Decimal` with currency-specific quantum (port `money.py`)
- IBAN/BIC: validated checksum before compare
- Reference text: normalized Unicode, stripped, embedding compared to approved template

**Standalone deploy:** Gate service called synchronously before payment API.

**Spine-connected:** Wire `reserve` holds funds; settle on rail confirmation; `HELD` wires go `STRANDED` until compliance adjudication.

```python
# Conceptual gate
match = semantic_matcher.score(wire.beneficiary, golden_record)
if wire.amount > golden_record.expected_amount * policy.max_amount_ratio:
    return GateResult.HELD(reason="AMOUNT_ANOMALY", match_score=match.score)
if match.score < policy.min_semantic_score:
    return GateResult.HELD(reason="BENEFICIARY_MISMATCH", match_score=match.score)
return GateResult.APPROVED
```

Program: [`programs/wire_match/`](../../programs/wire_match/)

---

## 3. SubledgerSync — Automated Subledger Reconciliation

### The problem

Multi-entity groups (UK/US entities, subsidiary brands) accumulate intercompany discrepancies from FX timing, rate source differences, and settlement lag. Errors surface months later at audit.

### The cost

Millions in lost tax efficiency, compounded audit fees, accounting team thrash.

### The code fix — SubledgerSync platform

**Event-driven reconciliation pipeline** with real-time FX and transaction hashing:

```
Entity A ledger ──► event bus ──► SubledgerSync ──► match graph
Entity B ledger ──► event bus ──►       │              │
                                        ├── FX rate API snapshot (hash stored)
                                        ├── intercompany pair matcher
                                        └── discrepancy alert at clear, not audit
```

**Core components:**

| Module | Responsibility |
|--------|----------------|
| `fx_snapshot.py` | Query ECB/Refinitiv/etc.; store rate + timestamp hash on each match attempt |
| `txn_hasher.py` | Canonical hash of (entity, counterparty, amount, currency, value_date) |
| `match_engine.py` | Graph pairing: same hash, mirrored amounts, FX within tolerance |
| `discrepancy_reporter.py` | Real-time alert when residual ≠ 0 after match window |

**Async IO:** Python `asyncio` + Postgres LISTEN/NOTIFY or Kafka consumer for high-throughput entity feeds.

**Standalone deploy:** Reconciler worker + Postgres; optional Neo4j for complex group structures.

**Spine-connected:** Matched pairs `settle`; unmatched go `STRANDED`; group `regulatory_ops` asserts zero orphaned intercompany after sweep.

```python
# Conceptual match
pair = match_engine.find_pair(txn_a, pending_b)
if pair and fx_snapshot.within_tolerance(pair, rate_source="ecb"):
    await reconciler.mark_matched(pair, fx_hash=fx_snapshot.hash)
else:
    await discrepancy_reporter.emit(txn_a, reason="NO_MIRROR_OR_FX_DRIFT")
```

Program: [`programs/subledger_sync/`](../../programs/subledger_sync/)

---

## 4. AssetLedger — Smart Asset Depreciation

### The problem

Institutions hold thousands of assets with complex depreciation schedules. Manual updates lag; books overstate value; tax and quarterly reporting drift from reality.

### The cost

Corporate tax overpayment, regulatory fines, inaccurate quarterly filings.

### The code fix — AssetLedger platform

**Programmatic asset ledger** with scheduled, regulation-driven write-downs:

```
Regulatory tables (HMRC, IRS) ──► table_sync job
                                        │
Asset registry ──► depreciation_engine ──► ledger postings
                        │
                        ├── cron-triggered run (daily, not year-end)
                        ├── method: straight-line, declining-balance per policy
                        └── append-only depreciation events
```

**Core components:**

| Module | Responsibility |
|--------|----------------|
| `asset_registry.py` | Asset ID, book value, method, jurisdiction, acquisition date |
| `reg_table_sync.py` | Pull HMRC / IRS rate tables; version + effective date |
| `depreciation_engine.py` | Compute period charge; never negative book value |
| `posting_emitter.py` | Event per write-down; GL bridge optional |

**"Smart contract" semantics without chain:** Cron job + immutable rule tables + append-only events = deterministic, auditable depreciation without blockchain overhead.

**Standalone deploy:** Engine + Postgres asset ledger + cron.

**Spine-connected:** Each write-down `settle` with `reg_table_version` in metadata; examiner export shows which regulatory table drove which charge.

```python
# Conceptual depreciation run
for asset in registry.due_for_depreciation(as_of=today):
    charge = engine.compute(asset, table=reg_tables.get(asset.jurisdiction))
    if charge > asset.book_value:
        charge = asset.book_value  # invariant: never negative
    ledger.post_depreciation(asset.id, charge, table_version=table.version)
```

Program: [`programs/asset_depreciation/`](../../programs/asset_depreciation/)

---

## Platform comparison

| Platform | Prevents | Standalone services | Key invariant |
|----------|----------|---------------------|---------------|
| **AlgoFreeze** | Runaway trades | 1 proxy | No egress when FROZEN |
| **WireMatch** | Wrong wire | 1 gate | No send below semantic threshold |
| **SubledgerSync** | IC drift | 1 reconciler | Discrepancy at clear, not audit |
| **AssetLedger** | Stale books | 1 engine + cron | Book value ≥ 0 always |
| **CreditGovern** | Ungoverned AI credit | 1 gate + mock rail | Reserve before inference |

---

## Build priority (revised)

| Order | Platform | Rationale |
|-------|----------|-----------|
| 1 | **AlgoFreeze** | Highest $/minute risk; clearest standalone demo; Knight narrative |
| 2 | **WireMatch** | Universal treasury pain; type-safety + NLP is concrete tech edge |
| 3 | **SubledgerSync** | Strong mid-market CFO buyer; async pipeline is well-scoped |
| 4 | **AssetLedger** | Steady value; regulatory table sync is differentiated |
| 5 | **CreditGovern** | Regulatory heavy; longer sales cycle |

All five share spine optional. AlgoFreeze + WireMatch demonstrate **pre-execution prevention** — the same philosophical core as ModelGovernor's reserve-before-dispatch.

---

## Demo commands (target)

```bash
# Standalone — each platform alone
make algofreeze-demo
make wirematch-demo
make subledger-demo
make assetledger-demo

# Spine-connected — unified audit
make fg-spine-up
make fg-all-platforms-demo   # cross-platform invariant drill
```
