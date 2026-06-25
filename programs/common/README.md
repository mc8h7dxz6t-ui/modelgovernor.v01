# Crystal Commit Protocol — Shared Module

CCP is implemented once in `platforms/common/crystal/` (target) and used by all Finance Governor platforms.

## API (target)

```python
def crystallize(
    platform: str,
    operation_id: str,
    risk_tier: str,
    facets: dict,
    parent_crystal_id: str | None = None,
) -> Crystal: ...

def commit(action: CommitAction, crystal_id: str) -> CommitResult: ...

def sweep_expired_horizons() -> list[Crystal]: ...  # → STRAND

def reconstruct(crystal_id: str) -> ReconstructionBundle: ...
```

## Platform integration

| Platform | Crystallize at | Commit at |
|----------|----------------|-----------|
| AlgoFreeze | FREEZE / version check | Order egress allowed |
| WireMatch | Gate evaluation | Rail send |
| SubledgerSync | Match attempt | Pair matched |
| AssetLedger | Depreciation run | Charge posted |
| CreditGovern | Reserve | Settle decision |

## Docs

- [crystal-commit-protocol.md](../../docs/finance-governor/crystal-commit-protocol.md)
