# Roadmap — 9/10 commercial viability (no section skipped)

**Goal:** Every section reaches **≥9/10** on a buyer-diligence rubric: technically complete, operable, sellable at **$80K–$150K ACV** (post-proof), not pre-revenue IP-only.

**Current honest baseline:** ~6–8/10 engineering on CG/MG core · ~3/10 commercial wrapper (SOC2, UI, support, logos).

**North star product:** **Governor Platform** — one spine library, three governor adapters, **two commercial wedges** (Cyber Commit Pack + Finance Commit Pack), optional MG spend gate.

**Non-negotiable:** Postgres production only · shadow → enforce · no delisted SKUs resurrected without regulatory path.

---

## Scoring rubric (what 9/10 means)

| Score | Meaning |
|-------|---------|
| **9–10** | Production pilot at named logo; procurement passes TPRM; runbooks + SLOs + tests prove behavior |
| **7–8** | Code complete; missing one of: logo, cert, or UI |
| **5–6** | Demo-ready; honest pilot only |
| **<5** | Spec, delisted, or marketing-only |

---

## Phase overview

| Phase | Focus | Exit gate |
|-------|--------|-----------|
| **P0** Foundation | Unify spine, merge IG, CI on all governors | Single `governor-core` package; all CI green on `main` |
| **P1** Wedge 9/10 | CG pack + FG WireMatch/AlgoFreeze production-hardened | 2 pilot-ready SKUs with runbooks |
| **P2** Platform 9/10 | Admin UI, observability, policy API | Auditor can review without CLI |
| **P3** Trust 9/10 | SOC2, pen test, GDPR erasure, threat model | TPRM packet complete |
| **P4** Commercial 9/10 | 3 pilots, marketplace, support model | $80K ACV defensible |

**Parallel tracks:** Engineering (P0–P2) and Trust (P3) overlap from week 8.

---

# Section 1 — Core spine unification (`governor-core`)

**Gold standard:** Single shared library (HashiCorp/Vault-style: one core, many products). DRY for crystallize, seal, reconciler, diagnostic mode.

| | Today | 9/10 target |
|---|------|-------------|
| **Score** | 6/10 (3 forks) | 9/10 |

### Build (working completion)

- [ ] Extract `packages/governor-core/` from duplicated MG/FG/CG sidecar logic:
  - `crystallize.py`, `chain_seal.py`, `reconciler_sweeper.py`, `diagnostic_mode.py`, `metrics.py`
- [ ] Domain adapters: `governor_core.mg`, `.fg`, `.cg` (event table names, facet schemas only)
- [ ] One migration toolkit; governors supply SQL deltas
- [ ] Property tests once on core (Hypothesis chain invariants)
- [ ] Versioned API: `GovernorSpineAdapter` interface documented

### Completion criteria

- Zero duplicate `ledger_seal` / `decision_seal` / `security_seal` logic across trees
- All three governors pass CI importing `governor-core`
- Architecture ADR checked in: `docs/adr/001-governor-core-extraction.md`

---

# Section 2 — Cyber Governor (commercial wedge #1)

**Gold standard:** NIST CSF 2.0 (Identify/Protect/Detect/Respond), ISO 27001 logging, SOC2 CC6/CC7 mapping, Okta/Zscaler **complement** positioning.

| | Today | 9/10 target |
|---|------|-------------|
| **Score** | 7.5/10 code · 4/10 GTM | 9/10 |

### Product: **CG Commit Pack** (sell as one SKU)

IdentityGate + EgressLock + Threat Mesh + spine. Other four platforms = add-ons.

### Build

- [ ] **Policy API:** `ENFORCE | SHADOW | MONITOR` per platform (env + HTTP header)
- [ ] **Production integrations (not mocks):**
  - Okta System Log webhook (WitnessBridge) — documented + tested with recorded fixtures
  - Generic HTTP witness + CloudTrail S3 path
  - Envoy/Istio filter stub OR documented sidecar injection pattern
- [ ] **Mesh rule DSL:** YAML rules validated at startup (`identity_gate.session_state=STRANDED → egress_lock`)
- [ ] **DLQ** for witness ingest (poison message quarantine)
- [ ] **Load test:** 500 RPS crystallize on Postgres (p95 < 100ms on reference hardware)
- [ ] **Runbook:** `docs/cyber-governor/operations-runbook.md` — diagnostic, strand queue, verify-chain failure
- [ ] **Grafana dashboard JSON:** mesh blocks, strands, chain verify status

### Completion criteria

- `make cg-load-test` passes SLO thresholds
- Shadow mode default in Helm values; enforce requires explicit values flag
- One **pilot deployment guide** < 20 pages, no hand-waving
- Pen test scope doc ready (even if test scheduled Phase 3)

---

# Section 3 — Finance Governor (commercial wedge #2)

**Gold standard:** MiFID II algo controls (AlgoFreeze), payment control (WireMatch), SR 11-7 **complement** (not replacement) for CreditGovern.

| | Today | 9/10 target |
|---|------|-------------|
| **Score** | 6/10 (2 demos) | 9/10 on 2 wedges |

### Product: **FG Commit Pack**

WireMatch + AlgoFreeze + spine. Subledger/Credit/Asset stay **L1** until Phase 5 optional.

### Build — WireMatch

- [ ] External **golden record** API (versioned beneficiary registry), remove hardcoded `_GOLDEN`
- [ ] SWIFT MX / ISO 20022 **field mapping** module (parse → internal `WireRequest`)
- [ ] HELD / REJECTED / APPROVED with crystal export for auditors
- [ ] Integration adapter interface: `PaymentRailAdapter` (stub + Modern Treasury-shaped mock)

### Build — AlgoFreeze

- [ ] Deploy SHA registry (file or OCI digest list)
- [ ] Feed heartbeat vector from pluggable `FeedHealthSource`
- [ ] EMS proxy integration doc + reference nginx/envoy config
- [ ] Sub-100ms FROZEN path load test

### Build — spine

- [ ] FG Postgres vigorous tests match MG parity (concurrent commit paths)
- [ ] `decision-chain-verify` CronJob verified in Helm dry-run CI
- [ ] Regulatory export API: `GET /internal/decisions/export?from=&to=` (JSON + optional PDF template)

### Completion criteria

- Fat-finger + Knight scenarios in automated E2E (`tests/e2e/fg_commit_pack/`)
- Examiner one-pager: what crystal proves vs what ValidMind proves

---

# Section 4 — ModelGovernor (commercial wedge #3)

**Gold standard:** FinOps reserve semantics; OWASP LLM Top 10 logging; complement to LiteLLM/Portkey.

| | Today | 9/10 target |
|---|------|-------------|
| **Score** | 7/10 | 9/10 |

### Build

- [ ] **LiteLLM compatibility layer:** drop-in proxy route documented + integration test
- [ ] **Shadow → enforce** on `POST /reserve` (policy flag)
- [ ] **Cryptographic erasure:** envelope encryption for PII in metadata; DEK destroy + tombstone event
- [ ] **Abuse limits:** per-API-key reserve rate limits; reconciler bulk strand resolution
- [ ] **FinOps export:** cost attribution dimensions → CSV for finance teams
- [ ] Deprecate marketing separate SKUs (SpendGuard = MG spine feature flag)

### Completion criteria

- `test_postgres_vigorous.py` + load harness green in CI every push
- Side-by-side doc: MG reserve vs LiteLLM Redis budget (falsifiable comparison)
- No claim of runtime model attestation (deployment-boundary only)

---

# Section 5 — Insurance Governor (merge + selective commercial)

**Gold standard:** Solvency II / claims controls narrative; **no NHS DTAC** unless Phase 6.

| | Today | 9/10 target |
|---|------|-------------|
| **Score** | 7/10 on branch · 0/10 on main | 9/10 on **ClaimGate + BindAuthority** only |

### Build

- [ ] Merge `cursor/insurance-governor-spine-254e` → `main`; IG CI on every push
- [ ] Commercial SKU: **IG Commit Pack** = ClaimGate + BindAuthority + spine
- [ ] Parametric / spatial / battery wedges → L1 or partner SOW
- [ ] Update HONEST-SCOPE + BUSINESS-MODEL for quad when merged

### Completion criteria

- `make ig-full-rehearsal` in CI
- FNOL → payout HELD scenario E2E
- No clinical/PHI positioning

---

# Section 6 — Data & persistence (Postgres HA)

**Gold standard:** AWS RDS / Cloud SQL patterns: Multi-AZ Postgres, PgBouncer, connection pooling, backup RPO/RTO documented.

| | Today | 9/10 target |
|---|------|-------------|
| **Score** | 7/10 | 9/10 |

### Build

- [ ] **Reference architecture:** RDS + PgBouncer + Redis Sentinel (one doc per cloud: AWS, GCP, Azure)
- [ ] Migrations: golang-migrate or Flyway-style versioning; rollback tested
- [ ] **Backup/restore runbook** with RPO ≤ 15 min, RTO ≤ 1 hr (buyer-managed)
- [ ] Chain verify on **read path** for auditor export (not only CronJob)
- [ ] Remove any doc implying SQLite in production paths

### Completion criteria

- Disaster recovery drill script: restore Postgres → verify-chain passes
- Connection pool metrics in Grafana

---

# Section 7 — Security & compliance (TPRM packet)

**Gold standard:** SOC 2 Type II (AICPA TSC), ISO 27001 alignment, GDPR Art. 17 erasure playbook, annual pen test (PTES-style).

| | Today | 9/10 target |
|---|------|-------------|
| **Score** | 4/10 (RLS + shadow shipped) | 9/10 |

### Build

- [x] **Postgres RLS tenant isolation** — `migrations/0013_tenant_rls.sql`, `sidecar/app/tenant_rls.py`, `docs/security/TENANT-RLS.md`
- [x] **Shadow/enforce intercept gate** — `sidecar/app/enforcement_mode.py`, wired on `/reserve` + `/settle`, `docs/security/SHADOW-ENFORCE.md`
- [x] **OIDC tenant claim** — JWKS-verified `tenant_id`; pool `RESET ALL` on checkout (ghost-tenant leak prevention)
- [ ] **Threat model:** `docs/security/THREAT-MODEL.md` — external/app/DBA/insider
- [ ] **SOC 2 Type I** readiness assessment → Type I report (month 4–6) → Type II (month 10–12)
- [ ] **Pen test** by qualified firm; remediate Critical/High; letter in data room
- [ ] **GDPR playbook:** PII-off-chain, DEK erasure, DPA template, subprocessor list
- [ ] **SBOM** per release (CycloneDX); dependency scan in CI (Grype/Trivy)
- [ ] **Secrets:** ESO/Vault patterns only; no default tokens in examples
- [ ] **mTLS** enterprise overlay tested in CI (already partial — complete for all governors)

### Completion criteria

- TPRM folder: SOC report + pen test + threat model + insurance cert ($2M+ cyber) — **or** explicit “vendor is subprocessors of acquirer” path
- No health/clinical claims in security packet

---

# Section 8 — Observability & SRE

**Gold standard:** Google SRE book — SLOs, error budgets, alerting; OpenTelemetry traces; Prometheus + Grafana.

| | Today | 9/10 target |
|---|------|-------------|
| **Score** | 6/10 | 9/10 |

### Build

- [ ] **SLO definitions:** availability 99.9% sidecar, p95 crystallize latency, reconciler lag < 30s
- [ ] **PrometheusRule** alerts shipped for all governors (partial exists — unify)
- [ ] **OpenTelemetry** traces: gateway → sidecar → platform (W3C trace context)
- [ ] **Synthetic probes** CronJob per governor (CG has — replicate MG/FG)
- [ ] **On-call runbook** with severity matrix (even if founder on-call for pilots)

### Completion criteria

- `docs/sre/slo.md` + `docs/sre/runbook.md`
- Grafana dashboard pack importable in 5 minutes
- Chaos test proves diagnostic mode fires alert

---

# Section 9 — Admin UI & auditor experience

**Gold standard:** Regulated buyers expect **read-only compliance UI** (ServiceNow GRC / Archer class **viewer**, not full GRC).

| | Today | 9/10 target |
|---|------|-------------|
| **Score** | 1/10 | 9/10 |

### Build (MVP — 4 views)

- [ ] **Governor Console** (React or HTMX — pick one, ship):
  1. **Crystal explorer** — filter by platform, decision, time
  2. **Strand queue** — adjudicate / release (role-gated)
  3. **Chain verify** — run + display `first_break`
  4. **Policy mode** — shadow/enforce per wedge
- [ ] OIDC login (same as spine); read-only default role
- [ ] Export CSV/PDF for auditor
- [ ] Embed path: iframe-friendly for Splunk/Datadog (optional)

### Completion criteria

- Non-technical user completes “show me why this wire was HELD” in < 3 minutes
- UI ships in Docker Compose demo stack (optional profile `docker compose --profile console`)

---

# Section 10 — Deployment & GitOps

**Gold standard:** Helm + Kustomize overlays; GitOps (ArgoCD/Flux); policy-as-code (OPA optional).

| | Today | 9/10 target |
|---|------|-------------|
| **Score** | 7/10 | 9/10 |

### Build

- [ ] **One Helm umbrella chart** `governor-platform` with subcharts: mg, fg, cg, console
- [ ] **Values matrix:** dev / staging / production / air-gapped
- [ ] ArgoCD Application manifests + upgrade runbook
- [ ] **Istio** STRICT mTLS tested end-to-end (enterprise overlay)
- [ ] **AWS Marketplace** listing (container + Helm) — Phase 4

### Completion criteria

- Fresh cluster deploy < 45 min following single doc
- CI: helm template + kubeconform on every push

---

# Section 11 — Testing & quality pyramid

**Gold standard:** Google/testing blog pyramid + financial institution preference for property tests on invariants.

| | Today | 9/10 target |
|---|------|-------------|
| **Score** | 7.5/10 | 9/10 |

### Build

| Tier | Target |
|------|--------|
| **T1** | Unit + SQLite fast < 3 min (keep) |
| **T2** | Postgres vigorous all governors every push |
| **T3** | Load harness SLO gates (fail CI on regression) |
| **T4** | Toxiproxy chaos all spines |
| **T5** | E2E: docker compose full walkthrough in CI (nightly) |
| **T6** | Contract tests for Okta/Stripe-shaped webhooks |

- [ ] Coverage floor: 80% on `governor-core` and platform gate modules
- [ ] Fuzz: JSON ingest on alt-data path (when/if revived)

### Completion criteria

- Badge in README: CI tiers 1–4 green; nightly E2E
- `make certification` runs full pyramid locally

---

# Section 12 — Documentation & data room

**Gold standard:** HashiCorp-style: install, operations, security, compliance — separate docs; data room zip for M&A.

| | Today | 9/10 target |
|---|------|-------------|
| **Score** | 6/10 | 9/10 |

### Build

- [ ] **HONEST-SCOPE** + **BUSINESS-MODEL-CRITIQUE** kept current (no resurrection of 12-SKU story)
- [ ] **Data room generator:** `make data-room` → zip with scope, threat model, test counts, architecture diagrams
- [ ] **API OpenAPI** specs published per platform service
- [ ] **RED-TEAM-RESPONSES** v2 maintained
- [ ] **Competitive battlecards** (1 page each: vs LiteLLM, vs Okta, vs ValidMind)

### Completion criteria

- Acquirer diligence answered from docs alone without founder call (4 hr review)

---

# Section 13 — Legal & commercial wrapper

**Gold standard:** MSAs used by B2B infra vendors (HashiCorp, Datadog templates as reference).

| | Today | 9/10 target |
|---|------|-------------|
| **Score** | 2/10 | 9/10 |

### Build

- [ ] **Pilot SOW template** — fixed scope, shadow mode, buyer ops responsibility, $25–40K
- [ ] **MSA + DPA** (UK/EU + US variants) — lawyer-reviewed
- [ ] **SLA schedule** — realistic: 8×5, 4h P1 for pilot; 24×7 only with SI partner
- [ ] **Insurance:** $2M cyber + $2M PI (minimum for mid-market TPRM)
- [ ] **Ltd co** with audited accounts path (even micro-audit)

### Completion criteria

- Legal packet attachable to every pilot proposal
- No £120K list price without “post-SOC2” footnote

---

# Section 14 — GTM & pilot factory

**Gold standard:** Bain B2B — one ICP, one wedge, repeatable 90-day pilot motion.

| | Today | 9/10 target |
|---|------|-------------|
| **Score** | 2/10 | 9/10 |

### Build

- [ ] **Three pilot playbooks:**
  1. CG Commit Pack — security platform 50–500 emp
  2. FG WireMatch — fintech treasury
  3. MG shadow — agent platform team
- [ ] **LOI template** → SOW → case study pipeline
- [ ] **Pricing page (private):** pilot / yr-1 / yr-2 ACV
- [ ] Kill reseller track until SOC2 + insurance

### Completion criteria

- **3 signed pilots** or **1 acquisition term sheet**
- 1 public case study (name or anonymized)

---

# Section 15 — Support & operating model

**Gold standard:** ITIL-light: incident, problem, change; PagerDuty integration.

| | Today | 9/10 target |
|---|------|-------------|
| **Score** | 1/10 | 9/10 |

### Build

- [ ] **Support tiers** documented: pilot vs production
- [ ] PagerDuty/Opsgenie webhook on Prometheus critical alerts
- [ ] **Status page** template (optional Instatus)
- [ ] **Release cadence:** semver, changelog, migration notes
- [ ] SI partner program doc (Deloitte/KPMG subprocessors) — Phase 4

### Completion criteria

- Pilot customer receives support playbook before go-live
- No “72h email patch” language anywhere

---

# What to build vs partner vs defer

| Item | Build | Partner | Defer |
|------|-------|---------|-------|
| Spine unification | ✅ | | |
| CG/FG wedges | ✅ | | |
| Admin console | ✅ (MVP) | Retool for internal only? | Full GRC suite |
| SOC2 | ✅ process | Vanta/Drata | |
| Pen test | | ✅ firm | |
| Webhook relay | | Svix/Hookdeck | Build |
| Clinical health | | | ❌ Phase 6+ |
| NHS framework | | | ❌ until DTAC |
| Reseller listing | | | ❌ until insurance + SOC2 |
| Full SIEM | | Splunk | Build |

---

# Suggested commercial SKU map (post-roadmap)

| SKU | Contents | Target ACV (yr 2) |
|-----|----------|-------------------|
| **CG Commit Pack** | Identity + Egress + mesh + spine | $80K–$150K |
| **FG Commit Pack** | WireMatch + AlgoFreeze + spine | $80K–$150K |
| **MG Spend Gate** | Reserve/settle + shadow/enforce | $60K–$120K |
| **IG Commit Pack** | ClaimGate + BindAuthority (post-merge) | $80K–$140K |
| **Governor Platform** | All packs + console + premium support | $200K–$350K |

**Not SKUs:** drift gate, spend guard, alt-data, webhooks (features or delisted).

---

# Phase gates (go/no-go)

| Gate | Requirement |
|------|-------------|
| **G0 → P1** | `governor-core` extracted; IG on main or explicitly deferred |
| **G1 → P2** | CG Commit Pack load test passes; FG golden record externalized |
| **G2 → P3** | Console MVP live; 1 pilot signed |
| **G3 → P4** | SOC2 Type I; pen test scheduled |
| **G4 → scale ACV** | 3 pilots + SOC2 Type II in progress |

---

# Team reality (minimum to hit 9/10)

| Role | FTE | Phase |
|------|-----|-------|
| Founder / spine architect | 1.0 | P0–P4 |
| Backend (governor-core + wedges) | 1.0 | P0–P2 |
| Frontend (console) | 0.5 | P2 |
| DevOps/SRE | 0.5 | P1–P3 |
| Security/compliance lead | 0.25 | P3 |
| Legal (external) | ad hoc | P3–P4 |

**Solo founder path:** P0 → P1 CG pack only → sell pilot or IP → hire from revenue. **Cannot 9/10 all sections solo in one pass** — sequence matters.

---

# Recommended build order (if you do one thing at a time)

1. **Merge IG + FG CI + HONEST-SCOPE** (credibility)
2. **`governor-core` extraction** (engineering debt)
3. **CG Commit Pack 9/10** (strongest sell)
4. **Console MVP** (unblocks procurement)
5. **FG WireMatch production** (second pilot SKU)
6. **SOC2 + pen test** (unblocks ACV)
7. **MG LiteLLM adapter + erasure** (agent market)
8. **3 pilots** (commercial proof)

---

## Related

- [HONEST-SCOPE.md](sales-sheets/HONEST-SCOPE.md)
- [BUSINESS-MODEL-CRITIQUE.md](sales-sheets/BUSINESS-MODEL-CRITIQUE.md)
- [cyber-governor/institutional-gold-standard.md](cyber-governor/institutional-gold-standard.md)
- [finance-governor/institutional-gold-standard.md](finance-governor/institutional-gold-standard.md)
