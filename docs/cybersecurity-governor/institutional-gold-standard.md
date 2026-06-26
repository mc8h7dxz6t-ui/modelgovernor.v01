# Institutional Gold Standard (Cybersecurity Governor)

Cybersecurity Governor inherits the ModelGovernor CCP (Crystallize-Commit-Provenance) spine and applies it to **runtime security enforcement** rather than claims or payments.

## Pillars

1. **Pre-execution gates** — ThreatProxy and EgressGovern block before dispatch, not after log ingestion.
2. **Cross-platform mesh** — Posture drift, identity violations, and threat blocks propagate to dependent platforms via `crystal_mesh_rules`.
3. **Provenance** — Hash-chained `security_events` with verify-chain and S3 Object Lock anchors.
4. **Fail-closed registry** — Unregistered platforms cannot crystallize when `platform_registry_enforce=true`.
5. **Enterprise zero-trust** — Istio mTLS with AuthorizationPolicy allowing only `cg-platform-workload` and `cg-gateway-workload` to reach sidecar :8121.

## Institutional++ bar

- 60+ automated tests including mesh behavioral tests
- Postgres vigorous + chaos (toxiproxy) tiers
- Helm L4 Gold enterprise overlay with HPA on egress and threat platforms
- Examiner evidence pack with SHA-256 attestation

See [security-enforcement-mesh.md](security-enforcement-mesh.md) for the primary differentiator vs GRC/SIEM rivals.
