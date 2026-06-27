# Cybersecurity Governor

Fourth governor in the ModelGovernor institutional++ lineage — **tamper-evident authorization ledger for security commits**.

L4 Gold = institutional test + deploy kit gate — not a Fortune 500 cyber product claim.

## What this is

| Layer | Purpose |
|-------|---------|
| **Spine** | Gateway / sidecar / reconciler — CCP, security escrow, hash chain, `security_ops` invariants |
| **Platforms** | Nine enforcement wedges (six sales SKUs + ThreatProxy, IR gate, ComplianceLogger) |

Sibling spines: ModelGovernor, Finance Governor, Insurance Governor — same reliability patterns, different domains.

## Architecture

```
cybersecurity-governor/
├── spine/                 # Control plane (ports 8120–8122)
├── platforms/             # Enforcement wedges (8123–8131)
├── migrations/
├── docker-compose.yml
└── docs → ../docs/cybersecurity-governor/
```

## Ports

| Service | Port |
|---------|------|
| cg-gateway | 8120 |
| cg-sidecar | 8121 |
| cg-reconciler | 8122 |
| egress_govern (CG-EGRESSLOCK) | 8123 |
| identity_govern (CG-IDENTITYGATE) | 8124 |
| threat_proxy | 8125 |
| incident_response_gate | 8126 |
| posture_reconcile (CG-POSTURERECONCILE) | 8127 |
| compliance_logger | 8128 |
| witness_bridge (CG-WITNESSBRIDGE) | 8129 |
| lineage_ingest (CG-LINEAGEINGEST) | 8130 |
| content_guard (CG-CONTENTGUARD) | 8131 |

## Quick start

```bash
make cg-spine-up          # spine only
make cg-stack-up          # spine + all platforms
make cg-spine-test        # unit + property tests
make cg-certification-l4-ci
make cg-egress-wedge-demo # defensible wedge: ext_authz + chain verify
make cg-security-demo     # multi-vector sales demo
```

## Defensible wedge

**Story:** No commit to exfil path without allowlisted crystal; parent identity violation blocks child egress commit.

1. `POST /session/arm` on IdentityGovern (8124)
2. Threat Mesh blocks egress commit when parent state is VIOLATION/DRIFT/BLOCKED
3. `POST /envoy/authz/check` on EgressGovern (8123) — wire Envoy ext_authz HTTP filter here
4. `GET /internal/security/verify-chain` on sidecar (8121)

## Sales SKU API map

| SKU | Platform | Key API |
|-----|----------|---------|
| CG-IDENTITYGATE | `identity_govern` | `POST /session/arm` |
| CG-EGRESSLOCK | `egress_govern` | `POST /egress/evaluate`, `POST /envoy/authz/check` |
| CG-WITNESSBRIDGE | `witness_bridge` | `POST /ingest/{okta\|cloudtrail\|generic}` |
| CG-LINEAGEINGEST | `lineage_ingest` | `POST /ingest/{falco\|tetragon\|generic}` |
| CG-POSTURERECONCILE | `posture_reconcile` | `POST /posture/evaluate` |
| CG-CONTENTGUARD | `content_guard` | `POST /content/evaluate` |

Full spec: [docs/cybersecurity-governor/institutional-gold-standard.md](../docs/cybersecurity-governor/institutional-gold-standard.md)
