# Finance Governor External Certification Program (FG-ECP)

**FG-ECP** extends internal Makefile gates (`fg-certification-l4`) with **self-generated attestation reports** suitable for vendor diligence folders. This is **not** accreditation by an independent auditor (SOC 2, ISO 27001).

## Levels

| Level | Audience | Key proof |
|-------|----------|-----------|
| **L3** | Platform vendors | SDK conformance + Postgres integration |
| **L4** | Enterprise deploy | L4 Gold Helm + chaos + GitOps |
| **L5 Institutional Self-Check** | Regulated production wiring | Live rails + RDS + Istio overlays + **self-run** attestation JSON |

Program manifest: [certification/program.yaml](../certification/program.yaml)

## Generate attestation report

```bash
cd finance-governor
make fg-certification-external              # L5 default
make fg-certification-external LEVEL=L4
python3 scripts/fg_certification_report.py L5 my_platform
```

Output: `artifacts/certification/fg-attestation-<platform>-<level>-<timestamp>.json`

Each report includes:

- `program_id` — FG-ECP version
- `level_claimed` — L3/L4/L5
- `git_commit` — build provenance
- `checks` — pass/fail per requirement with evidence path
- `report_sha256` — SHA-256 digest of canonical report body (tamper-evident)

## Partner submission workflow

1. Complete [partner-checklist.md](../certification/partner-checklist.md)
2. Run `make fg-platform-conformance` and `make fg-certification-l4`
3. Generate attestation: `make fg-certification-external PLATFORM=my_platform`
4. Archive report in GRC / vendor risk system
5. Optional: examiner pack via `GET /internal/regulatory/export` + chain verify

## Internal vs external certification

| Gate | Type | Command |
|------|------|---------|
| Platform SDK | Internal CI | `make fg-platform-conformance` |
| L4 Gold | Internal CI | `make fg-certification-l4` |
| **FG-ECP attestation** | **External vendor** | `make fg-certification-external` |

Internal gates block merges. External attestation is the **vendor deliverable** for RFP and SOC2 evidence folders.

## L5 Institutional Self-Check requirements

**Not** SOC 2 Type II or ISO 27001 — see [operational-architecture-scorecard.md](../../governor-spine-core/docs/operational-architecture-scorecard.md).

- **Live inference rails** — `FG_CREDIT_RAIL_MODE=live` with HTTP provider (`inference_rail.py`)
- **Managed Postgres** — `values-rds.yaml` overlay (no in-cluster StatefulSet)
- **Istio all workloads** — `istio.enabled: true` in enterprise values
- **Attestation report** — generated and archived with `report_sha256`

## Related

- [capability-matrix.md](../../docs/finance-governor/capability-matrix.md)
- [l4-certification.md](l4-certification.md)
- [platform-sdk.md](platform-sdk.md)
