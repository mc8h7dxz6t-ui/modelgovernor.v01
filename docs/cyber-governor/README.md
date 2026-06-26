# Cybersecurity Governor — Platform Vision

**Cybersecurity Governor** adapts the ModelGovernor institutional++ control-plane spine for security operations — plus **specialized platforms** that each solve a costly multi-vector IR problem and can run **alone or plugged into the spine**.

### Unique IP: Threat Crystal Protocol (TCP)

No security surprise is allowed to authorize without a **Threat Crystal**:

- **Threat Crystal** — immutable, hash-chained snapshot of identity/lineage/posture at arm time
- **Session Horizon** — risk-tiered TTL; ambiguity **strands**, never guesses
- **Threat Mesh** — cross-platform invariants when spine-connected
- **Forensic Reconstruction** — rebuild decision context without re-running sensors

→ [threat-crystal-protocol.md](threat-crystal-protocol.md)

## Platform model

| Platform | Shadow Gap solved | Standalone? |
|----------|-------------------|-------------|
| [IdentityGate](../../cyber-governor/platforms/identity_gate/) | Session hijack / token binding mismatch | ✅ |
| [EgressLock](../../cyber-governor/platforms/egress_lock/) | Ungoverned data exfiltration | ✅ |
| [WitnessBridge](../../cyber-governor/platforms/witness_bridge/) | Log erasure / telemetry silence | ✅ |

**Optional spine** (gateway :8100 + ledger sidecar :8101 + reconciler :8102) unifies TCP, audit, Threat Mesh, and forensic export.

→ Full spine spec: [spine.md](spine.md) · Code: [`cyber-governor/`](../../cyber-governor/)

## Why this exists

Multi-vector attacks exploit **The Shadow Gap** — evidence fragmented across clocks, ephemeral workloads, and mutable logs. Incumbent SIEM/XDR correlates probabilistic alerts. Cybersecurity Governor **binds authorization to cryptographic crystals** before irreversible security actions.

| Gap | Incumbent tooling | Cybersecurity Governor edge |
|-----|-------------------|----------------------------|
| Time-skew | Correlation windows | Append-only hash chain + causal parent IDs |
| Ephemeral erasure | Lost after TTL | Crystal-bound proxy capture at action time |
| Log mutation | Trust local logs | Witness ingest + silence detection |
| False-positive fatigue | ML correlation scores | Deterministic structural lineage + strand semantics |
| Deploy flexibility | All-or-nothing suites | Each platform functions alone or on spine |

## Document map

| Document | Purpose |
|----------|---------|
| [spine.md](spine.md) | Spine architecture — gateway/sidecar/reconciler |
| [threat-crystal-protocol.md](threat-crystal-protocol.md) | Unique IP — Threat Crystal Protocol |
| [platform-model.md](platform-model.md) | Standalone vs spine-connected deployment |
| [integrations.md](integrations.md) | Works with Okta, CloudTrail, generic webhooks |
| [institutional-gold-standard.md](institutional-gold-standard.md) | **Industry++ reliability** — invariants, SLOs, framework mapping |
| [capability-matrix.md](capability-matrix.md) | RFP / diligence checklist |
| [reliability-testing.md](reliability-testing.md) | 4-tier test pyramid |
| [slo-definitions.md](slo-definitions.md) | SLIs, alerts, error budget |
| [quality-bar.md](quality-bar.md) | Merge gate |

## Relationship to sibling governors

```
ModelGovernor          → LLM reserve / settle
Finance Governor       → Crystal commit / wire / algo
Cybersecurity Governor → Threat crystal / session / egress / witness
```

All three share: idempotency, append-only events, hash chain, diagnostic mode, reconciler leader election, K8s HA patterns.

## Quick start

```bash
# Standalone platform
CG_SPINE_ENABLED=false make identity-gate-demo

# Full stack
make cg-stack-up
make cg-spine-test
make threat-crystal-demo
```
