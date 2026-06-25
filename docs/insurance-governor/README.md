# Insurance Governor Documentation

Runtime insurance commit control plane — sibling to [ModelGovernor](../architecture.md) and [Finance Governor](../finance-governor/README.md).

| Document | Purpose |
|----------|---------|
| [platform-model.md](platform-model.md) | Standalone vs spine-connected deployment |
| [institutional-gold-standard.md](institutional-gold-standard.md) | Reliability and invariant requirements |
| [warranty-enforcement-engine.md](warranty-enforcement-engine.md) | Cross-platform mesh = policy warranty enforcement |
| [insurer-persona-mapping.md](insurer-persona-mapping.md) | Loss control positioning for Cyber, D&O, E&O, Crime |
| [uk-us-regulatory-framework.md](uk-us-regulatory-framework.md) | FCA/PRA/Solvency II + NAIC/ECOA mapping |
| [market-gaps-insurance.md](market-gaps-insurance.md) | Underserved insurer gaps and wedge strategy |
| [design-partner-attestation.md](design-partner-attestation.md) | Pilot credibility package |

Implementation: [`insurance-governor/`](../../insurance-governor/)

## Quick commands

```bash
make ig-spine-test    # Tier 1 tests
make ig-stack-up      # Spine + ClaimGate
make claim-gate-demo  # Payout gate smoke
```
