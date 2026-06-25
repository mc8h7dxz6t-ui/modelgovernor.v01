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
| [integration-architecture.md](integration-architecture.md) | FNOL, write-back, rails, oracle topology |
| [completion-checklist.md](completion-checklist.md) | 100% automated completion matrix |
| [production-infrastructure.md](production-infrastructure.md) | Mock → live: Postgres, bank/oracle feeds, Istio mTLS |
| [insurance-governor-tomorrow-sale.md](../sales-sheets/insurance-governor-tomorrow-sale.md) | **Asset sale spec** — per-platform vs competitor, pre-revenue ask |

Implementation: [`insurance-governor/`](../../insurance-governor/)

## Quick commands

```bash
make ig-spine-test    # Tier 1 tests
make ig-stack-up      # Spine + ClaimGate
make claim-gate-demo  # Payout gate smoke
make ig-full-rehearsal # Enterprise rehearsal + published data room
```
