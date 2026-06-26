# Institutional++ Gold Standard — Cybersecurity Governor

What **industry gold standard with institutional++ grade** means for Cybersecurity Governor — testable, operable, examiner-defensible.

## Definition

**Institutional++** satisfies three audiences simultaneously:

1. **Engineering** — correct under failure, provable invariants, tested through Tier 4
2. **Operations** — SLOs, CronJobs, diagnostic mode (no poison pill)
3. **Risk / Compliance** — tamper-evident audit, NIST/SOC mapping, witness quorum

## Five non-negotiable design principles

1. **Postgres is authoritative** — Redis is never the ledger
2. **Fail closed on authorize, fail open on reads** — diagnostic mode
3. **Tamper-evident audit** — hash chain + verify CronJob + S3 anchor
4. **Strand-not-guess** — critical/high horizon → `STRANDED`, never silent allow
5. **Single-writer reconciliation** — leader election; idempotent sweeps preserve chain

## Surprise Budget = 0 (TCP invariants)

| Signal | Meaning |
|--------|---------|
| `surprise_authorize_blocked_total` | Commit without valid crystal |
| `threat_fingerprint_mismatch_total` | Facet drift at commit |
| `threat_horizon_strand_total` | Ambiguity stranded |
| `threat_mesh_block_total` | Cross-platform mesh violation |
| `security_audit_violation_total` | Post-sweep invariant failure |

Any unexpected increase → **diagnostic mode** + P1 investigation.

## Reliability stack

```
Ingress (platforms / webhooks / lineage)
         │
         ▼
Gateway :8100 ──► Sidecar :8101 (3+ replicas)
         │              │
         │              ├── Redis (diagnostic, guardrails)
         │              ├── security_events hash chain
         │              └── threat_crystals / action_escrow
         ▼
Reconciler :8102 (leader)
  • horizon_sweep (sealed STRANDED events)
  • security_ops + threat_ops audit
         │
         ▼
Witness quorum: security_chain_anchors + S3 Object Lock
```

## Framework mapping

| Framework | Cybersecurity Governor evidence |
|-----------|--------------------------------|
| **NIST CSF** | Detect (lineage), Respond (strand), Recover (reconciler) |
| **ISO 27001** | Hash chain, S3 anchor, access control |
| **SOC 2 Type II** | OIDC RBAC, admin_audit_log, invariant probes, CronJobs |
| **MITRE D3FEND** | Provenance (TCP), isolation (mesh, NetworkPolicy) |
| **Zero Trust** | Crystallize-before-authorize, continuous verification |

## 4-tier test pyramid

| Tier | Command | Status |
|------|---------|--------|
| 1 SQLite unit | `make cg-spine-test` | ✅ 25+ tests |
| 2 Postgres | `make cg-postgres-test` | ✅ |
| 3 Live demo | `make cg-security-demo` | ✅ |
| 4 K8s gate | `make cg-deploy-dry-run` | ✅ |

See [reliability-testing.md](reliability-testing.md), [capability-matrix.md](capability-matrix.md), [slo-definitions.md](slo-definitions.md).

## Production checklist (L4 Gold)

- [x] Hash chain verify every 15m
- [x] Anchor head hourly to Postgres + S3
- [x] Synthetic canary every 5m
- [x] Governance canary every 10m
- [x] PrometheusRule alerts
- [x] DB CHECK constraints (migration 0003)
- [x] NetworkPolicy + strand egress template
- [x] OIDC on privileged paths (sidecar + gateway)
- [x] PgBouncer + Redis Sentinel (production overlay)
- [x] Istio mTLS + egress allowlist (enterprise overlay)
- [x] Istio AuthorizationPolicy adapter → spine (enterprise overlay)
- [ ] Helm chart + ArgoCD (Phase 4 roadmap)
