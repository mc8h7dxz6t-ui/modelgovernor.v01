# Data room samples — NOT Phase C evidence

Files in this directory are **demonstration samples** for sales and engineering rehearsal.

They **fail** `spine_core.attestation_validate.phase_c_valid()` because:

- `environment` is `local-embedded-rehearsal` (not customer VPC / production)
- No signed design-partner letter accompanies these JSON files

For IL rubric row 5 (Phase C), produce:

`artifacts/reliability/insurance-governor/cluster_attestation.json`

from a **buyer VPC** run with `IG_CLUSTER_ATTESTATION=true` and `IG_ATTESTATION_ENV=customer-vpc-staging`.

See [artifacts/reliability/README.md](../../../artifacts/reliability/README.md).
