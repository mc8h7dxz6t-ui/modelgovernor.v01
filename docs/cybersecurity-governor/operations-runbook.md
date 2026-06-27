# Cybersecurity Governor — Operations Runbook

## Spine ports

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

## Health checks

```bash
curl -sf http://localhost:8121/healthz
curl -sf -H 'x-internal-token: $TOKEN' http://localhost:8121/internal/security/verify-chain
```

## Security Enforcement Mesh

When posture drift, threat block, identity violation, or egress deny is committed, dependent platforms are blocked at commit time via `crystal_mesh_rules`. See [security-enforcement-mesh.md](security-enforcement-mesh.md).

## Incident response

1. Enter diagnostic mode via admin API to halt writes without data loss.
2. Export examiner bundle: `GET /internal/regulatory/export`
3. Verify chain: `GET /internal/security/verify-chain`
4. Anchor head: `POST /internal/security/anchor-head`

## Enterprise deploy

```bash
helm upgrade --install cg ./deploy/helm/cybersecuritygovernor \
  -f values-production.yaml -f values-enterprise.yaml
```
