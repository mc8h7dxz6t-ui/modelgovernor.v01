# SOC 2 Evidence Pack (Cybersecurity Governor)

Evidence artifacts for CC6 (logical access), CC7 (monitoring), and CC8 (change management) mapped to CG controls.

## Control mapping

| SOC 2 control | CG artifact |
|---------------|-------------|
| CC6.1 logical access | IdentityGovern + OIDC RBAC on `/internal/*` |
| CC6.6 boundary protection | EgressGovern allowlist + Istio STRICT mTLS |
| CC7.2 anomaly detection | ThreatProxy pre-dispatch score gate |
| CC7.3 evaluation of events | Hash-chained `security_events` + verify-chain API |
| CC8.1 change management | Platform registry + manifest hash enforcement |

## Automated evidence

```bash
make cg-examiner-evidence
```

Produces `artifacts/certification/cg_examiner_evidence.json` with SHA-256 manifest.

## Manual operator evidence

- Helm enterprise render: `make cg-helm-enterprise`
- Chain verification cron: `security-chain-verify` CronJob
- S3 Object Lock anchors: `SECURITY_ANCHOR_S3_*` config
