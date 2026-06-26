# Institutional++ gold standard

Cybersecurity Governor inherits ModelGovernor's institutional++ reliability bar. See also [Finance Governor institutional-gold-standard.md](../finance-governor/institutional-gold-standard.md) for the full pattern catalog.

## Inherited capabilities

| Capability | Cybersecurity Governor implementation |
|------------|--------------------------------------|
| Append-only audit | `security_events` + SHA-256 hash chain |
| Idempotency | `platform + operation_id` unique on `threat_crystals` |
| Strand-not-guess | Critical/high horizon expiry → `STRANDED` |
| Diagnostic write-halt | Sidecar `diagnostic_mode` blocks mutations |
| Reconciler leader | Horizon sweeper with `FOR UPDATE SKIP LOCKED` |
| Invariant counters | `surprise_authorize_blocked_total`, mesh blocks |
| 4-tier CI | Unit (SQLite) → Postgres → load → chaos (port from ModelGovernor kit) |

## Security-specific invariants

| Invariant | Enforcement |
|-----------|-------------|
| No authorize without crystal | Commit path requires valid `crystal_id` |
| Fingerprint match | Commit facets must equal crystallize facets |
| Threat Mesh | Parent STRANDED blocks child egress commit |
| Witness silence | WitnessBridge tracks `silent_sources` (demo threshold) |

## SLO targets (spine)

| SLI | Target |
|-----|--------|
| `/crystallize` success rate | 99.5% / 30d |
| `/crystallize` p95 latency | ≤ 500ms |
| `/commit` success rate | 99.5% / 30d |
| Horizon strand correctness | 100% (invariant) |

## Regulatory / compliance mapping

| Requirement | TCP artifact |
|-------------|--------------|
| Immutable audit trail | Hash-chained `security_events` |
| Access decision record | Threat crystal facets at arm time |
| Incident reconstruction | `/internal/crystals/{id}/reconstruct` |
| Separation of duties | Internal token + optional OIDC RBAC (Phase 3) |

## Test tiers

```bash
# Tier 1 — SQLite unit (< 1s)
cd cyber-governor && make cg-spine-test

# Tier 2+ — port ModelGovernor postgres/chaos harness with cyber schema
```
