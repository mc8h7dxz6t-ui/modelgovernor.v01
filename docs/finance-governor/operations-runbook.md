# Finance Governor Operations Runbook

Incident response and operational procedures for the Finance Governor spine and platforms.

## Service map

| Service | Port | Health |
|---------|------|--------|
| Gateway | 8090 | `GET /readyz` |
| Sidecar | 8091 | `GET /healthz`, `GET /readyz` |
| Reconciler | 8092 | `GET /healthz` |
| WireMatch | 8093 | `GET /healthz` |
| AlgoFreeze | 8094 | `GET /healthz` |
| SubledgerSync | 8095 | `GET /healthz` |
| AssetLedger | 8096 | `GET /healthz` |
| CreditGovern | 8097 | `GET /healthz` |

## Severity 1 — Decision chain verification failed

**Symptoms:** `FgDecisionChainVerificationFailed` alert; `GET /internal/decisions/verify-chain` returns `valid: false`.

**Actions:**
1. Enter diagnostic mode (writes halt automatically if `diagnostic_mode_blocks_writes=true`).
2. Export forensic bundle: `GET /internal/regulatory/export`.
3. Do not clear diagnostic until root cause identified.
4. Compare `decision_chain_anchors` head with recomputed chain.
5. Escalate to platform engineering with export JSON.

## Severity 1 — Reserve availability SLO breach

**Symptoms:** `FgReserveAvailabilityLow` alert; elevated `surprise_commit_blocked_total`.

**Actions:**
1. Check Postgres and Redis connectivity on sidecar pods.
2. Verify `account_ledgers` balances for affected desks.
3. Review recent `guardrail_incidents` and drift lockouts.
4. Scale sidecar replicas if CPU-saturated.

## Severity 2 — Exposure drift lockout

**Symptoms:** Account `active=false`, `lock_reason=DRIFT_THRESHOLD_EXCEEDED`; `drift_enforced_total` increment.

**Actions:**
1. Identify operation via `GET /internal/guardrail/incidents`.
2. Reconstruct crystal: `GET /internal/crystals/{id}/reconstruct`.
3. Confirm committed vs reserved exposure in escrow ledger.
4. Financial admin may re-enable account after remediation (manual SQL or admin tooling).

## Severity 2 — Diagnostic mode active

**Symptoms:** `503 diagnostic mode: writes halted` on crystallize/commit.

**Actions:**
1. `GET /internal/diagnostic/status` for trigger reason.
2. Run `regulatory_ops` invariant probes via reconciler logs.
3. After fix, `POST /internal/diagnostic/clear` (requires financial-admin OIDC or internal token).

## Routine operations

### Hourly chain verify (CronJob)

Helm chart deploys `decision-chain-verify` CronJob. Manual check:

```bash
curl -sf -H "x-internal-token: $TOKEN" \
  http://fg-sidecar:8091/internal/decisions/verify-chain
```

### Hourly S3 anchor

```bash
curl -sf -X POST -H "x-internal-token: $TOKEN" \
  http://fg-sidecar:8091/internal/decisions/anchor-head
```

### Examiner export

```bash
curl -sf -H "x-internal-token: $TOKEN" \
  http://fg-sidecar:8091/internal/regulatory/export > fg-export-$(date +%Y%m%d).json
```

### Certification suite

```bash
cd finance-governor && make fg-certification
```

### Full platform demo

```bash
make fg-all-platforms-demo
make fg-demo-gold-reliability
```

## Deployment

```bash
make fg-helm-install          # production values
kustomize build deploy/kustomize/overlays/production
```

Enable Prometheus SLO rules in production values:

```yaml
prometheusRules:
  enabled: true
```

## Contacts

- **Financial admin:** OIDC role `financial-admin`
- **Compliance viewer:** OIDC role `compliance_viewer`
- **On-call:** platform SRE rotation
