# Data room — Insurance Governor

Redacted design-partner materials for investor and wholesale broker due diligence.

| File | Purpose |
|------|---------|
| [design-partner-attestation-redacted.md](design-partner-attestation-redacted.md) | NDA-safe attestation excerpt (PDF-ready) |
| [design-partner-package.json](design-partner-package.json) | Artifact hashes + probe summary |

Regenerate after cluster run:

```bash
make ig-cluster-attestation
make ig-design-partner-package
```

Live probe artifact (not committed — gitignored): `artifacts/reliability/insurance-governor/cluster_attestation.json`
