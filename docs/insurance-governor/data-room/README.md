# Data room — Insurance Governor

Redacted design-partner materials for investor and wholesale broker due diligence.

| File | Purpose |
|------|---------|
| [design-partner-attestation-redacted.md](design-partner-attestation-redacted.md) | NDA-safe attestation excerpt (PDF-ready) |
| [design-partner-package.json](design-partner-package.json) | Artifact hashes + probe summary |
| [published/](published/) | Committed rehearsal artifacts (cluster + certification + manifest) |
| [design-partner-signed-letter.template.md](design-partner-signed-letter.template.md) | NDA letter template with hash placeholders |

Regenerate after cluster run:

```bash
make ig-cluster-attestation
make ig-design-partner-package
```

Full enterprise rehearsal (stack + FedNow sandbox + published data room):

```bash
make ig-full-rehearsal      # Docker HTTP stack (preferred on Mac)
make ig-embedded-rehearsal  # No Docker — in-process probes (7/7)
```

`publish_data_room.py` rejects stub attestations (0/0 probes). Published bundle must come from one of the commands above.

Live probe artifact (not committed — gitignored): `artifacts/reliability/insurance-governor/cluster_attestation.json`
