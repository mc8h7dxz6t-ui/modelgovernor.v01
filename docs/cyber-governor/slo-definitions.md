# Cybersecurity Governor — SLO Definitions

| SLI | Measurement | Target (30d) |
|-----|-------------|--------------|
| Crystallize availability | `crystallize_success / crystallize_total` | ≥ 99.5% |
| Crystallize latency p95 | `/crystallize` response time | ≤ 500ms |
| Commit availability | `commit_success / commit_total` | ≥ 99.5% |
| Security chain validity | `security_chain_verification_ok` | 100% (invariant) |
| Anchor success | `security_chain_anchor_recorded` hourly | 100% |
| Horizon strand correctness | `threat_ops` post-sweep audit | 100% (invariant) |

## Burn-rate alerts (Prometheus)

See `cyber-governor/deploy/base/prometheus-rules.yaml`:

- `CybersecurityGovernorSecurityChainInvalid` — critical
- `CybersecurityGovernorSecurityAnchorFailed` — warning
- `CybersecurityGovernorThreatHorizonStrand` — warning (informational strand events)

## Error budget policy

TCP invariants (`surprise_authorize_blocked`, `threat_fingerprint_mismatch`, `security_audit_violation`) have **zero error budget** — any increase triggers diagnostic mode and P1 investigation.
