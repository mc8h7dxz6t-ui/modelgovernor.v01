# Insurance Governor Operations Runbook

Incident response and operational procedures for the Insurance Governor spine and platforms.

## Service map

| Service | Port | Health |
|---------|------|--------|
| Gateway | 8100 | `GET /readyz` |
| Sidecar | 8101 | `GET /healthz`, `GET /readyz` |
| Reconciler | 8102 | `GET /healthz` |
| ClaimGate | 8103 | `GET /healthz` |
| BindAuthority | 8104 | `GET /healthz` |
| ParametricOracle | 8105 | `GET /healthz` |
| ZkClaimAudit | 8106 | `GET /healthz` |
| SpatialTwin | 8107 | `GET /healthz` |
| BatteryLiability | 8108 | `GET /healthz` |
| SubrogationGraph | 8109 | `GET /healthz` |
| IndemnityPayGate | 8110 | `GET /healthz`, `GET /metrics` |
| ModelRiskFreeze | 8111 | `GET /healthz`, `GET /metrics` |
| UnderwritingGovern | 8112 | `GET /healthz` |
| ReserveReconcile | 8113 | `GET /healthz` |

## Severity 1 — Claim chain verification failed

**Symptoms:** `IgClaimChainVerificationFailed` alert; `GET /internal/claims/verify-chain` returns `valid: false`.

**Actions:**
1. Enter diagnostic mode (writes halt; reads remain available).
2. Export forensic bundle: `GET /internal/crystals/{id}/reconstruct` for affected operations.
3. Do not clear diagnostic until root cause identified.
4. Compare `claim_chain_anchors` head with recomputed chain.
5. Escalate to platform engineering with chain verify JSON.

```bash
curl -sf -H "x-internal-token: $TOKEN" \
  http://ig-sidecar:8101/internal/claims/verify-chain | jq .
```

## Severity 1 — Crystallize / commit availability SLO breach

**Symptoms:** `IgCrystallizeAvailabilityLow` or elevated `surprise_commit_blocked_total`.

**Actions:**
1. Check Postgres and Redis connectivity on sidecar pods.
2. Verify `reserve_ledgers` balances for affected carrier accounts.
3. Review `guardrail_incidents` and mesh block events (`crystal_mesh_block_total`).
4. Scale sidecar replicas if CPU-saturated.

## Severity 2 — Warranty mesh block storm

**Symptoms:** Spike in `crystal_mesh_block_total`; child platform commits return HTTP 409.

**Actions:**
1. Identify parent platform breach: ModelRiskFreeze `FROZEN`, ClaimGate `REFERRED`, etc.
2. Reconstruct parent crystal: `GET /internal/crystals/{crystal_id}/reconstruct`.
3. Remediate parent condition (unfreeze model, clear SIU referral, reconcile reserves).
4. Confirm mesh rule in `crystal_mesh_rules` is intentional — not misconfigured facet value.

## Severity 2 — ModelRiskFreeze desk frozen

**Symptoms:** `403 MODEL_FROZEN` on `/inference/evaluate`; `version_mismatch_freeze_total` increment.

**Actions:**
1. `GET /status?jurisdiction=US` on ModelRiskFreeze (8111).
2. Compare `runtime_version` vs `approved_version`.
3. If legitimate deploy: `POST /admin/approved-version` with new approved SHA.
4. Verify mesh unblocks ClaimGate / IndemnityPayGate after parent crystal updates.

## Severity 2 — IndemnityPayGate held payments

**Symptoms:** `indemnity_payee_held_total` or `indemnity_fat_finger_held_total` increment; payments HELD.

**Actions:**
1. Review payee name/account vs golden record for jurisdiction.
2. Check `social_engineering_flag` on FNOL source.
3. Confirm amount within `max_amount_ratio` of expected indemnity.
4. Manual adjudication path via ClaimGate SIU if fraud suspected.

## Severity 2 — Diagnostic mode active

**Symptoms:** `503 diagnostic mode: writes halted` on crystallize/commit.

**Actions:**
1. `GET /internal/diagnostic/status` for trigger reason.
2. Run `claim_ops` invariant probes via reconciler logs.
3. After fix, `POST /internal/diagnostic/clear` (requires claims-admin OIDC or internal token).

## Severity 3 — Redis / guardrail degradation

**Symptoms:** `guardrail_degraded_total`, `local_fallback_crystallize_total` increment.

**Actions:**
1. Verify Redis Sentinel or single-node Redis health.
2. Confirm local fallback limits are bounding traffic (not unbounded bypass).
3. Restore Redis; confirm `dependency_circuit_open_total` returns to baseline.

---

## Failure mode matrix

| Failure | User-visible behavior | Data integrity | Recovery |
|---------|----------------------|----------------|----------|
| Redis down | Local fallback rate limits; crystallize may continue bounded | Postgres authoritative | Restore Redis |
| Postgres down | 503 on `/readyz`; no commits | No partial writes | Failover / restore |
| Reconciler partition | Single leader via advisory lock; no double-sweep | Idempotent sweeps | Leader election resumes |
| Diagnostic mode | Writes 503; reads 200 | Chain frozen | Admin clear after root cause |
| Mesh parent breach | Child commit 409 | Parent crystal non-terminal | Fix parent facet state |
| S3 anchor failure | `claim_chain_anchor_s3_failed_total` | Chain intact locally | Retry anchor CronJob |
| Toxiproxy / network partition | Elevated latency; claim_ops must stay zero | Chaos CI proves invariants | Reset proxy / network |

---

## Routine operations

### Hourly chain verify (CronJob)

Helm chart deploys `ledger-verify` CronJob. Manual check:

```bash
curl -sf -H "x-internal-token: $TOKEN" \
  http://ig-sidecar:8101/internal/claims/verify-chain
```

### Hourly S3 anchor

```bash
curl -sf -X POST -H "x-internal-token: $TOKEN" \
  http://ig-sidecar:8101/internal/claims/anchor-head
```

### Examiner evidence pack

```bash
make ig-examiner-evidence
# → insurance-governor/artifacts/certification/ig-examiner-evidence-*.json
```

### Certification suite

```bash
make ig-certification           # standard L4 gate
make ig-certification-strict    # + chaos + live chain verify (Docker + stack)
```

### Enterprise rehearsal

```bash
make ig-full-rehearsal          # full HA + data room publish
make ig-embedded-rehearsal      # offline fallback (no Docker)
```

### Mesh warranty demo

```bash
make ig-stack-up
make ig-demo
pytest insurance-governor/tests/test_mesh_warranty.py -v
```

---

## Deployment

```bash
helm lint deploy/helm/insurancegovernor
helm upgrade --install insurancegovernor deploy/helm/insurancegovernor \
  -f deploy/helm/insurancegovernor/values-production.yaml
```

Enable Prometheus rules in production values:

```yaml
prometheusRules:
  enabled: true
```

---

## Contacts

- **Claims admin:** OIDC role `claims-admin`
- **Compliance viewer:** OIDC role `compliance_viewer`
- **On-call:** platform SRE rotation
