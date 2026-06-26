# Tier-1 Carrier PoC — Deployment Playbook

**SKU:** `IG-PLATFORM-PRODUCTION` + `EVAL` license (30–90 days)  
**Audience:** Carrier CISO, CRO office, Chief Claims Officer, Guidewire integration lead  
**Outcome:** Signed design-partner LOI or paid `DP` conversion with attestation hash on record

---

## Executive summary

| | |
|---|---|
| **Duration** | 30 days (minimum) · 60 days (recommended) · 90 days (full wedge proof) |
| **Environment** | Buyer staging VPC (preferred) or vendor-hosted isolated cluster |
| **Scope** | Spine + ClaimGate + ParametricOracle + one headline wedge |
| **Out of scope** | Production claim payments, live FedNow without buyer keys, PAS replacement |
| **Success criteria** | Hash chain valid · mesh block demonstrated · FNOL ingest · examiner pack green |

---

## Phase 0 — Commercial & legal (Week −2 to 0)

| Step | Owner | Deliverable |
|------|-------|-------------|
| Execute mutual NDA | Legal | NDA + data-processing addendum |
| Sign evaluation schedule | Commercial | `EVAL` license — Exhibit A SKUs from [IP licensing framework](05-ip-licensing-framework.md) |
| Name pilot sponsor | Carrier | CRO or Chief Claims Officer letter of intent (non-binding) |
| Identify PAS source | Integration | Guidewire / Snapsheet / Majesco sandbox tenant |
| VPC decision | Infra | Buyer AWS account ID or dedicated EKS cluster name |

**Gate:** Written approval to receive Helm values + attestation scripts (no prod PII in vendor environment).

---

## Phase 1 — Infrastructure baseline (Days 1–5)

### 1.1 Target topology

```
Internet / carrier DMZ
        │
   IG Gateway :8100 (OIDC)
        │
   IG Sidecar :8101 (hash-chained claim_events)
        │
   ┌────┴────┬──────────────┬─────────────┐
   ▼         ▼              ▼             ▼
ClaimGate  ParametricOracle  ModelRiskFreeze*  Postgres HA
 :8103         :8105            :8111          + PgBouncer
```

\*Optional headline wedge — swap for IndemnityPayGate (Crime) or ReserveReconcile (Actuarial).

### 1.2 Deploy commands

```bash
# Vendor delivers tagged release (e.g. v0.1.0-l4-gold)
helm upgrade --install ig ./deploy/helm/insurancegovernor \
  -f deploy/helm/insurancegovernor/values-production.yaml \
  -f deploy/helm/insurancegovernor/values-enterprise.yaml \
  --set secrets.create=false \
  --set externalSecrets.enabled=true

# Buyer populates ExternalSecrets:
#   database-url, sidecar-internal-tokens, oidc-issuer-url, oidc-audience

# Verify render
helm lint deploy/helm/insurancegovernor \
  -f values-production.yaml -f values-enterprise.yaml
```

### 1.3 Infrastructure checklist

| Component | Requirement | Verify |
|-----------|-------------|--------|
| Postgres 16 | RDS/Aurora or in-cluster + PgBouncer | Migrations `0001`–`0009` applied |
| Redis Sentinel | Guardrails (optional staging) | Sidecar `/readyz` |
| OIDC IdP | Carrier Entra / Okta tenant | `test_auth_oidc.py` equivalent |
| Istio | STRICT mTLS enterprise overlay | `sidecar-ingress-platforms` policy active |
| Egress | FedNow / USGS allowlisted or stub mode | `PAYMENT_RAIL_MODE=stub` for PoC |
| NetworkPolicy | Platform → sidecar :8101 open | `test_l5_network_policy_allows_platform_to_sidecar` |

### 1.4 Day-5 gate

- [ ] All pods ready (`kubectl get pods -n insurancegovernor`)
- [ ] `GET /healthz` on gateway, sidecar, claim-gate
- [ ] `GET /internal/claims/verify-chain` → `valid: true` (empty chain OK)

---

## Phase 2 — Integration wiring (Days 6–12)

### 2.1 FNOL webhook path

| Step | Action |
|------|--------|
| 1 | Register ClaimGate in platform registry (migration `0005` or admin API) |
| 2 | Configure Guidewire/Snapsheet sandbox webhook → `POST https://<gateway>/claim/fnol/webhook` |
| 3 | Map vendor header auth → gateway OIDC or internal token |
| 4 | Run 10 synthetic FNOL payloads — confirm `NormalizedFnol` path |

```bash
# Local rehearsal before carrier webhook
make ig-stack-up
make ig-pilot-attestation
```

### 2.2 Payment rail (stub only for PoC)

```yaml
integrations:
  paymentRailMode: stub   # NOT fednow until buyer provides BANK_RAIL_API_TOKEN
```

Document in pilot report: *"No production claim payments executed."*

### 2.3 ParametricOracle (optional cat line)

- `ORACLE_FEED_MODE=mock` for week 2; switch to `live` + USGS for week 3 if egress approved.
- Demonstrate `sha256(source:payload)` gate blocks tampered feed.

### 2.4 Day-12 gate

- [ ] ≥50 FNOL events ingested (synthetic or sandbox)
- [ ] Duplicate idempotency key returns same `payment_id` (Postgres `payment_idempotency`)
- [ ] SIU referral path blocks IndemnityPayGate commit (mesh demo)

---

## Phase 3 — Loss-control proof exercises (Days 13–22)

Run scripted scenarios from [warranty-enforcement-engine.md](../insurance-governor/warranty-enforcement-engine.md):

| # | Scenario | Expected outcome | Leakage class addressed |
|---|----------|------------------|-------------------------|
| 1 | ModelRiskFreeze → FROZEN → ClaimGate commit | **Blocked** at mesh | E&O / model drift payout |
| 2 | ClaimGate REFERRED → IndemnityPayGate | **Blocked** | Fraud / SIU leakage |
| 3 | ReserveReconcile DRIFT → payout | **Blocked** | Reserve inadequacy |
| 4 | IndemnityPayGate semantic payee mismatch | **Blocked** | Crime / social engineering |
| 5 | Policy limit exceeded on ClaimGate | **Blocked** at policy rules | Severity leakage |

Record crystal IDs and `verify-chain` output after each scenario.

```bash
make ig-certification-l4-ci          # 35+ gates
make ig-examiner-evidence            # SOC2-style pack
make ig-design-partner-package       # Redacted data room
```

### 3.1 Load rehearsal (optional Days 20–22)

```bash
# Requires POSTGRES_TEST_URL or staging DB
LOAD_WORKERS=8 LOAD_OPS_PER_WORKER=10 pytest insurance-governor/tests/load/test_claim_gate_production.py -q
```

Target: zero idempotency failures under concurrent FNOL.

---

## Phase 4 — Executive readout (Days 23–30)

### 4.1 Attestation bundle (deliver to CRO / CISO)

| Artifact | Path |
|----------|------|
| Cluster attestation JSON | `artifacts/reliability/insurance-governor/cluster_attestation.json` |
| Certification attestation | `artifacts/reliability/insurance-governor/latest_attestation.json` |
| Redacted data room | `docs/insurance-governor/data-room/design-partner-attestation-redacted.md` |
| SHA-256 manifest | `docs/insurance-governor/data-room/published/manifest.json` |

### 4.2 Readout agenda (90 min)

| Time | Topic | Audience |
|------|-------|----------|
| 0:00 | PoC objectives recap | Sponsor + CRO delegate |
| 0:10 | Live demo: FNOL → governed commit → chain verify | Claims + integration |
| 0:35 | Mesh block scenarios (leakage prevention) | CRO + actuarial |
| 0:55 | Security: mTLS, NetPol, OIDC, examiner pack | CISO |
| 1:10 | Gap honesty FAQ | All |
| 1:20 | Conversion paths: `DP` → `SUB-VPC` | Commercial |

### 4.3 Success / no-go criteria

| Result | Criteria | Next step |
|--------|----------|-----------|
| **Go** | All Phase 3 scenarios pass; chain valid; sponsor sign-off | Convert to `DP` or `SUB-VPC` SOW |
| **Extend** | Integration gaps only (IdP, egress) | 30-day extension on `EVAL` |
| **No-go** | Chain invalid or mesh bypass found | Root-cause + patch release before retry |

---

## Roles & RACI

| Activity | Vendor | Carrier IT | Carrier Claims | CRO office |
|----------|--------|------------|----------------|------------|
| Helm deploy | C | R | I | I |
| OIDC / secrets | C | R | I | A |
| FNOL mapping | C | C | R | I |
| Scenario execution | C | I | R | A |
| Attestation sign-off | C | I | C | **A** |

R = Responsible · A = Accountable · C = Consulted · I = Informed

---

## Risk register (pre-written for RFP)

| Risk | Mitigation |
|------|------------|
| PAS team bandwidth | Vendor provides webhook replay (`SKU-WEBHOOK-REPLAY`) |
| IdP delay | Staging internal-token fallback (disabled in prod overlay) |
| Examiner questions on ZK | Position as SHA-256 commitment + selective disclosure (roadmap: SNARK) |
| Production payment scope creep | Contract explicitly limits `PAYMENT_RAIL_MODE=stub` for PoC |

---

## Conversion pricing (illustrative post-PoC)

| Path | Year 1 | Notes |
|------|--------|-------|
| Design-partner `DP` | £45K–£90K | Staging, single entity, attestation included |
| Production `SUB-VPC` | £180K–£320K | Spine + ClaimGate + 1 wedge |
| Perpetual `PERP-VPC` | £350K–£550K | + 15% Yr2 maintenance |

---

## Related

- [Design-partner attestation](../insurance-governor/design-partner-attestation.md)
- [Production infrastructure](../insurance-governor/production-infrastructure.md)
- [CRO deck layout](07-cro-claims-leakage-deck.md)
- [IP licensing framework](05-ip-licensing-framework.md)
