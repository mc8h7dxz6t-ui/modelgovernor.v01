# Phase C — External evidence (path to IL 9/10)

Industry Leading **9/10** requires row 5 of the IL rubric: a design-partner or acquirer runs attestation in their VPC and archives validated JSON plus a redacted signed letter.

## Per-governor artifact paths

| Governor | Cluster attestation path |
|----------|--------------------------|
| ModelGovernor | `artifacts/reliability/modelgovernor/cluster_attestation.json` |
| Finance Governor | `artifacts/reliability/finance-governor/cluster_attestation.json` |
| Cybersecurity Governor | `artifacts/reliability/cybersecurity-governor/cluster_attestation.json` |
| Insurance Governor | `artifacts/reliability/insurance-governor/cluster_attestation.json` |

## Validate before data-room publish

```bash
PYTHONPATH=governor-spine-core python3 -c "
from pathlib import Path
from spine_core.attestation_validate import load_cluster_attestation, validate_cluster_attestation
path = Path('artifacts/reliability/cybersecurity-governor/cluster_attestation.json')
errors = validate_cluster_attestation(load_cluster_attestation(path))
assert not errors, errors
print('Phase C OK')
"
```

## Required fields (no stubs)

- `probes_total` / `probes_passed` ≥ 7
- `artifact_sha256` (SHA-256 of canonical JSON)
- `probes[]` with live probe results
- `environment` must **not** be `ci-mock`
- **No** `probes_note` stub field

Pilot attestation JSON from `*-pilot-attestation` is **not** sufficient for IL 9/10 — promote to `cluster_attestation.json` after VPC run.
