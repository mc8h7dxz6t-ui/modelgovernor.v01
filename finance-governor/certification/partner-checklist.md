# Finance Governor Partner Certification Checklist

Use this checklist when certifying a **third-party platform** for spine integration. Submit the generated attestation report (`make fg-certification-external`) to your compliance or vendor-risk team.

## Pre-submission

- [ ] Platform registered in `platform_registry` with `facet_schema` and `base_url`
- [ ] `instrument_policy_registry` policy row (if exposure reserve required)
- [ ] `PlatformConfig` + `create_platform_app()` or equivalent observability contract
- [ ] `FG_SPINE_ENABLED=false` standalone path verified
- [ ] `FG_SPINE_ENABLED=true` spine path verified

## L3 Institutional++ (minimum for production spine)

- [ ] `make fg-platform-conformance` passes
- [ ] `make fg-integration-test` passes (Postgres)
- [ ] Facet schema matches crystallize payloads
- [ ] Idempotent `operation_id` on all mutations
- [ ] Invariant counters documented with zero error budget

## L4 Gold (enterprise fleet)

- [ ] Helm `platforms.fleet[]` entry or dedicated Deployment
- [ ] PodMonitor / metrics scrape configured
- [ ] NetworkPolicy egress compatible (if enterprise overlay)
- [ ] `make fg-certification-l4` passes in CI

## L5 Institutional Self-Check (self-generated attestation — not SOC2)

- [ ] Live provider integration (not mock-only) with circuit breaker
- [ ] RDS / managed Postgres overlay (`values-rds.yaml`) if production
- [ ] Istio sidecar injection on all platform pods (`istio.enabled: true`)
- [ ] Attestation report generated via `make fg-certification-external` and archived
- [ ] Examiner evidence pack: regulatory export sample + chain verify output

**Not included:** accredited third-party audit (SOC 2 Type II, ISO 27001).

## Generate attestation

```bash
cd finance-governor
make fg-certification-external
# Output: artifacts/certification/fg-attestation-<timestamp>.json
```

## Vendor attestation fields

| Field | Description |
|-------|-------------|
| `platform_name` | Registry name (e.g. `my_platform`) |
| `level_claimed` | L3, L4, or L5 |
| `git_commit` | Build provenance |
| `checks` | Pass/fail per program requirement |
| `report_sha256` | Tamper-evident digest of report body |

## Related

- [program.yaml](program.yaml)
- [external-certification.md](../docs/external-certification.md)
