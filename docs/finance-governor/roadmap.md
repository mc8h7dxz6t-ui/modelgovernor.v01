# Finance Governor Roadmap

Phased build: **standalone platforms first**, optional spine for unified audit.

## Phase 0 — Design and alignment ✅ complete

**Status:** Superseded by L5 Industry Leading delivery (see `finance-governor/docs/l4-certification.md`, `external-certification.md`).

**Deliverables:**
- [x] Market gap analysis (`market-gaps.md`)
- [x] Governance framework mapping (`governance-framework.md`)
- [x] Architecture specification (`architecture.md`)
- [x] Platform model — standalone vs spine (`platform-model.md`)
- [x] Code-driven fixes deep dive (`code-driven-fixes.md`)
- [x] Five platform program specs (`programs/`)
- [ ] Stakeholder sign-off on AlgoFreeze as first build

**Success criteria:**
- Each platform has standalone deploy spec
- Spine integration contract agreed (`spine_adapter`)
- Demo narrative per platform validated

---

## Phase 1 — First standalone platform: AlgoFreeze

**Goal:** Deployable heartbeat proxy preventing order egress on version mismatch or feed gap. No spine required.

### Deliverables

| Item | Details |
|------|---------|
| `platforms/algofreeze/` | Proxy + version_guard + feed_heartbeat + freeze_controller |
| `docker-compose.standalone.yml` | Proxy + Redis + Postgres |
| `platform_events` table | Local append-only audit |
| `make algofreeze-demo` | Version mismatch → FREEZE → no egress |
| Tests | `tests/programs/algofreeze/` |

### Success criteria

```bash
make algofreeze-demo
pytest tests/programs/algofreeze/
```

- Freeze on version mismatch in < 100ms
- Zero orders egress when FROZEN
- Runs without any spine service

---

## Phase 1b — Second standalone: WireMatch

**Goal:** Semantic wire gate with Decimal type-safety. No spine required.

### Deliverables

| Item | Details |
|------|---------|
| `platforms/wire_match/` | Gate + semantic_matcher + execution_gate |
| `make wirematch-demo` | Beneficiary mismatch → HELD |
| Tests | Amount anomaly, type-safety, standalone mode |

---

## Phase 2 — Spine scaffold + platform adapters

**Goal:** Optional spine; platforms opt in via `FG_SPINE_ENABLED`.

### Deliverables

| Item | ModelGovernor reference |
|------|------------------------|
| `spine/sidecar/` | Port `sidecar/` skeleton |
| `platforms/common/spine_adapter.py` | reserve/settle/emit with local fallback |
| AlgoFreeze + WireMatch spine mode | Cross-platform demo |
| `regulatory_ops.py` | Port `finance_ops.py` |
| `make fg-spine-up` | Spine + 2 platforms |

### Success criteria

- Platforms work identically with `FG_SPINE_ENABLED=false`
- Spine mode adds hash chain + cross-platform invariants
- AlgoFreeze freeze visible in spine event stream

---

## Phase 3 — Remaining platforms (standalone each)

| Platform | Deliverable |
|----------|-------------|
| SubledgerSync | FX-hash match pipeline + `make subledger-demo` |
| AssetLedger | Cron depreciation + `make assetledger-demo` |
| CreditGovern | Reserve-before-score + mock rail |

Each ships standalone before spine integration.

---

## Phase 4 — Institutional hardening

**Goal:** Production-grade reliability matching ModelGovernor capability matrix.

### Deliverables

| Item | Details |
|------|---------|
| Hash-chained `decision_events` | Port `ledger_seal.py` |
| `admin_audit_log` | Privileged mutation trail |
| Diagnostic mode | Write halt on invariant violation |
| OIDC + RBAC | `risk_admin`, `compliance_viewer`, `model_owner` |
| Exposure drift lockout | Port drift enforcement from `ledger.py` |
| Multi-rail failover | `inference_rail_attempts` |
| Attribution API | By desk, book, tenant, model version |
| Guardrail incidents | Approval required, bias, version mismatch |
| Prometheus metrics + SLO rules | 99.5% reserve availability |
| Integration test suite | 50+ tests, property-based ledger tests |
| `programs/credit_decision_governance/` | Full program with README |

### Success criteria

```bash
make fg-demo-gold           # 11-step institutional walkthrough
pytest tests/integration/   # vigorous Postgres suite
pytest tests/programs/credit_decision_governance/
```

- Replay protection validated
- Reconciler safe under concurrent execution
- Chain verification API passes
- Drift lockout demo step works

---

## Phase 3 — Production deployment kit

**Goal:** Repeatable K8s install for pilot banks.

### Deliverables

| Item | Details |
|------|---------|
| Kustomize overlays | staging, production, enterprise |
| Helm chart | `deploy/helm/financegovernor/` |
| PgBouncer + Redis Sentinel | Production overlay |
| ExternalSecrets | Vault / AWS SM |
| S3 Object Lock anchoring | Hourly chain head |
| Ledger verify CronJob | Hourly |
| Synthetic credit probe CronJob | 5-min canary |
| ArgoCD application | GitOps |
| Istio enterprise overlay | mTLS + egress allowlist |
| Operations runbook | Incident response |
| Regulatory export API | `GET /internal/regulatory/export` |

### Success criteria

```bash
helm install financegovernor deploy/helm/financegovernor -f values-staging.yaml
kustomize build deploy/overlays/production | kubectl apply --dry-run=client -f -
```

- Pilot deploy in < 1 day from docs
- SLO alerts firing in Prometheus
- Examiner export produces valid JSON bundle

---

## Phase 4 — Second wedge (fraud/AML)

**Goal:** Prove platform is instrument-agnostic.

### Deliverables

- `instrument_type = fraud` policies
- Screen reserve → settle semantics
- Analyst disposition as settlement
- Shared reconciler, new program tests

### Success criteria

- Same spine, new program tests pass without sidecar core changes
- Policy registry drives behavior, not code forks

---

## Phase 5 — Enterprise expansion

| Feature | Priority |
|---------|----------|
| Admin UI for compliance officers | High |
| Batch decision import | Medium |
| Multi-currency FX snapshots | Medium |
| Bias dashboard (cohort analytics) | High |
| Double-entry GL posting bridge | Low (partner integration) |
| SOC 2 Type II evidence pack | High for US banks |

---

## Build order (Phase 1 detail)

1. `finance-governor/migrations/0001_init.sql` — core tables
2. `finance-governor/sidecar/app/decision_ledger.py` — reserve/settle
3. `finance-governor/sidecar/app/regulatory_ops.py` — invariants
4. `finance-governor/gateway/app/governance.py` — orchestration
5. `finance-governor/reconciler/app/sweeper.py` — expiry/strand
6. Mock inference rail in gateway
7. Docker Compose wiring
8. Integration tests
9. `scripts/fg-demo-gold.sh`

---

## Risk register

| Risk | Mitigation |
|------|------------|
| Scope creep into full LOS/AML platform | Strict wedge: governance layer only, integrate via API |
| Regulatory interpretation variance | Jurisdiction tags + policy registry, not hardcoded rules |
| PII in ledger | Reference hashes only; vault integration Phase 2 |
| ModelGovernor drift | Pin spine copy to tagged MG release; document port map |
| Sales cycle length | `make fg-demo-gold` as 5-min proof artifact |

---

## Metrics for program success

| Metric | Phase 1 | Phase 3 |
|--------|---------|---------|
| Integration tests | 20 | 80+ |
| Invariant probes | 6 | 12 |
| Demo steps | 5 | 11 |
| SLO definitions | 0 | 2 (availability, latency) |
| Chaos tests | 0 | Toxiproxy finance ops tier |
