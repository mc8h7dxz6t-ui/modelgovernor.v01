# Insurance Governor Documentation

Runtime insurance commit control plane — sibling to [ModelGovernor](../architecture.md) and [Finance Governor](../finance-governor/README.md).

| Document | Purpose |
|----------|---------|
| [platform-model.md](platform-model.md) | Standalone vs spine-connected deployment |
| [institutional-gold-standard.md](institutional-gold-standard.md) | Reliability and invariant requirements |

Implementation: [`insurance-governor/`](../../insurance-governor/)

## Quick commands

```bash
make ig-spine-test    # Tier 1 tests
make ig-stack-up      # Spine + ClaimGate
make claim-gate-demo  # Payout gate smoke
```
