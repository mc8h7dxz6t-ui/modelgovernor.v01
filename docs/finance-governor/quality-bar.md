# Finance Governor Quality Bar

Extends ModelGovernor `docs/quality-bar.md` for standalone platforms and optional spine.

## Standard

Every Finance Governor change must preserve:

- **Pre-execution control** — gate, freeze, or reserve before irreversible action
- **Institutional-grade audit** — append-only events, no silent mutation
- **Standalone viability** — platform works without spine
- **Deterministic recovery** — reconciler or explicit strand, not hope

Reject prototype patterns, float money math, and spine-required coupling.

## Platform merge checklist

- [ ] Pre-execution gate tested (cannot bypass)
- [ ] Idempotency on all mutations
- [ ] Invariant probes with zero error budget documented
- [ ] Standalone `docker-compose` boots in one command
- [ ] `FG_SPINE_ENABLED=false` path tested
- [ ] Failure modes in runbook or platform README
- [ ] Prometheus counters for material events

## Spine merge checklist (additional)

- [ ] Hash chain verify passes
- [ ] Diagnostic mode: writes halt, reads live
- [ ] Cross-platform invariants documented if applicable
- [ ] Tier 2 Postgres tests pass
- [ ] SLO recording rules present

## Vocabulary

Use: institutional++, ledger-backed, pre-execution, tamper-evident, deterministic, strand, invariant, fail-closed.

Avoid: "AI-powered" without mechanism, "blockchain" for append-only Postgres, "100% secure."

## Related

- `docs/quality-bar.md` (ModelGovernor)
- `docs/finance-governor/institutional-gold-standard.md`
