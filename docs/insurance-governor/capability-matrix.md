# Insurance Governor — Capability Matrix (institutional++)

Use in carrier RFPs, Lloyd's diligence, and state DOI model-risk questionnaires. Status reflects **implemented** state on the L4 Gold track.

**Deep dives:** [institutional gold standard](institutional-gold-standard.md) · [warranty enforcement engine](warranty-enforcement-engine.md) · [operations runbook](operations-runbook.md)

## Certification levels

| Level | Requirements | Verify |
|-------|--------------|--------|
| **L1 Platform** | Standalone ClaimGate + spine adapter local mode | `make ig-spine-test` |
| **L2 Institutional** | + diagnostic mode, `claim_ops` probes | Tier 1 pytest |
| **L3 Institutional++** | + hash chain verify, anchor, guardrails + fallback | `GET /internal/claims/verify-chain` |
| **L4 Gold** | + 4-tier CI, Helm HA, load harness, chaos | `make ig-certification` |
| **L4 Gold Strict** | + chaos required + live chain verify | `make ig-certification-strict` |
| **Enterprise rehearsal** | + data room publish, cluster attestation | `make ig-full-rehearsal` |

Legend: ✅ Implemented · 🔌 Deploy-time config · 📄 Documented operator step

---

## Capability matrix (current)

| Capability | Status | Demo / test | Production |
|------------|--------|-------------|------------|
| Reserve-before-payout (crystallize + reserve) | ✅ | `make ig-demo` | Gateway + sidecar |
| ClaimGate policy + SIU gate | ✅ | `make claim-gate-demo` | Port 8103 |
| FNOL ingest (6 vendors) | ✅ | `test_fnol_adapter.py` | Webhook adapters |
| FNOL write-back | ✅ | `test_fnol_writeback.py` | Guidewire / Acturis / ICE |
| Payment rails (FedNow sandbox/live) | ✅ | `make ig-rail-smoke` | `bank_rail.py` |
| **Warranty Enforcement Mesh** (6 rules) | ✅ | `test_mesh_warranty.py` | `crystal_mesh_rules` |
| **ModelRiskFreeze** version gate | ✅ | `test_loss_control_wedges.py` | Port 8111 |
| **IndemnityPayGate** semantic payee gate | ✅ | `test_platform_invariant_counters.py` | Port 8110 |
| UnderwritingGovern fairness gate | ✅ | `test_loss_control_wedges.py` | Port 8112 |
| ReserveReconcile drift gate | ✅ | `test_loss_control_wedges.py` | Port 8113 |
| Per-wedge invariant counters | ✅ | `ig_platform_invariant_events_total` | Platform `/metrics` |
| Append-only `claim_events` + hash chain | ✅ | `verify-chain` API | Postgres |
| 7 zero-budget `claim_ops` probes | ✅ | `test_postgres_vigorous.py` | Reconciler sweep |
| Leader-elected reconciler | ✅ | `test_reconciler_leader_election.py` | 2+ replicas |
| Redis guardrails + local fallback | ✅ | `test_guardrails.py` | Sidecar |
| Dependency circuit breaker | ✅ | `test_circuit_breaker.py` | Sidecar |
| Diagnostic mode (no poison pill) | ✅ | Auto | Redis / API flag |
| S3 Object Lock external anchor | ✅ | `test_claim_anchor_s3.py` | Helm CronJob |
| OIDC JWT RBAC | ✅ | `test_auth_oidc.py` | Gateway + sidecar |
| Platform registry plug-and-play | ✅ | `test_platform_sdk.py` | Migration `0005` |
| ParametricOracle attestation hash | ✅ | `test_oracle_feed.py` | Port 8105 |
| ZkClaimAudit commitments | ✅ | `test_zk_claim_audit.py` | SHA-256 (not SNARK) |
| Helm HA kit (PgBouncer, Sentinel) | ✅ | `helm lint` CI | `deploy/helm/insurancegovernor` |
| Istio STRICT mTLS overlay | ✅ | Helm template | Enterprise overlay |
| Prometheus SLOs + P1 rules | ✅ | `/metrics/prometheus` | `prometheus-rules.yaml` |
| Governance + synthetic canaries | ✅ | Helm CronJobs | K8s |
| 4-tier CI (unit → Postgres → load → chaos) | ✅ | `.github/workflows/ci.yml` | GitHub Actions |
| Examiner evidence pack | ✅ | `make ig-examiner-evidence` | Attestation JSON + SHA256 |
| Data room publish | ✅ | `make ig-embedded-rehearsal` | `data-room/published/` |
| 90+ automated tests | ✅ | `pytest insurance-governor/tests/` | CI |

---

## Governance pillar coverage

| Pillar | Key capabilities |
|--------|------------------|
| **Regulatory Compliance** | UK/US framework mapping, per-bind crystals, adverse-action flags |
| **Risk Management** | Mesh blocks, reserve holds, model freeze, payee semantic gate |
| **Accountability** | Admin audit log, crystal reconstruct, design-partner attestation |
| **Monitoring** | Spine + wedge invariant counters, SLOs, synthetic probes |
| **Transparency** | Hash chain, verify API, S3 anchor, selective disclosure (ZkClaimAudit) |

---

## Competitive positioning

| vs. | Insurance Governor edge |
|-----|-------------------------|
| **PAS (Guidewire, Duck Creek)** | Runtime warranty mesh + hash-chained commit control |
| **Fraud / SIU (Shift, FRISS)** | SIU **blocks commit**, not just scores |
| **MRM (ModelOp, Monitaur)** | **Freeze → block indemnity** at runtime |
| **GRC suites** | Sub-second pre-execution gate with examiner proof |
| **Service mesh** | Domain semantics: reserves, facets, mesh rules |

---

## Regulatory evidence mapping

| Examiner question | Proof artifact |
|-------------------|----------------|
| How do you prevent payout on wrong model version? | ModelRiskFreeze + mesh block + `version_mismatch_freeze_total` |
| How do you block crime/social engineering payments? | IndemnityPayGate + `indemnity_social_engineering_blocked_total` |
| Prove the claim log wasn't tampered with | `GET /internal/claims/verify-chain` + S3 anchor |
| Cross-product warranty enforcement? | `crystal_mesh_rules` + `crystal_mesh_block_total` |
| Third-party attestation? | `make ig-examiner-evidence` → `pack_sha256` |

---

## Proof commands

```bash
make ig-demo
make ig-certification
make ig-certification-strict    # Docker + stack required
make ig-examiner-evidence
make ig-embedded-rehearsal
pytest insurance-governor/tests/test_mesh_warranty.py -v
pytest insurance-governor/tests/test_platform_invariant_counters.py -v
```
