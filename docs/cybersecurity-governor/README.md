# Cybersecurity Governor

Fourth governor in the ModelGovernor institutional++ lineage — **runtime security enforcement** with L4 Gold certification parity.

## Quick start

```bash
make cg-spine-up          # spine only (8120–8122)
make cg-stack-up          # spine + nine platforms (8123–8131)
make cg-certification-l4-ci
```

## Documentation

- [Capability matrix](../docs/cybersecurity-governor/capability-matrix.md)
- [Institutional gold standard](../docs/cybersecurity-governor/institutional-gold-standard.md)
- [Security Enforcement Mesh](../docs/cybersecurity-governor/security-enforcement-mesh.md)
- [L4 certification](../docs/cybersecurity-governor/l4-certification.md)

## Ports

| Component | Port |
|-----------|------|
| Gateway | 8120 |
| Sidecar | 8121 |
| Reconciler | 8122 |
| EgressGovern | 8123 |
| IdentityGovern | 8124 |
| ThreatProxy | 8125 |
| IncidentResponseGate | 8126 |
| PostureReconcile | 8127 |
| ComplianceLogger | 8128 |
