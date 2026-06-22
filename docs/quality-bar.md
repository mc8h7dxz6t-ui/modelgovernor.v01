# Quality Bar

## Standard

Every change to `modelgovernor.v01` must preserve and strengthen the repository's core identity:

- institutional-grade governance
- reliable and robust operation
- policy-enforced controls
- auditable system behavior
- provider-agnostic portability
- deterministic financial and operational handling

Reject changes that feel prototype-like, weaken trust boundaries, blur system-of-record ownership, or introduce hidden operational risk.

## Architecture quality bar

Every architectural change must preserve clear separation of responsibilities:

- **Gateway** handles provider-compatible request routing
- **Sidecar** handles policy, reserve, settle, refund, auth, and control logic
- **Postgres** is the source of truth for ledger and audit state
- **Redis** is only for volatile runtime guardrails
- **Reconciler** handles stale reservation repair and recovery

### Must-haves
- No ambiguous ownership of state
- No duplicate truth across Redis and Postgres
- No governance-critical logic hidden in the gateway if it belongs in the sidecar
- No direct provider egress from components that should be governed

## Data and ledger quality bar

All financial or usage-accounting logic must be institutional-grade.

### Required
- Exact-decimal values for monetary fields
- Explicit state transitions
- Idempotency for reserve, settle, and refund paths
- Append-only style event capture for all material transitions
- Deterministic reconciliation behavior
- Clear terminal reasons for failures or expiry

### Must never happen
- Floating-point billing math
- Silent balance mutation
- Overwriting historical audit meaning
- Non-idempotent settlement paths
- Ambiguous reservation status transitions

## API and service quality bar

All APIs must look deliberate and production-minded.

### Required
- Typed request and response models
- Explicit validation
- Stable endpoint naming
- Clear error categories
- Idempotency handling where applicable
- Internal auth on privileged paths
- Timeouts and operational boundaries considered

## Reliability and robustness quality bar

Every change must improve or preserve operational robustness.

### Required
- Safe failure handling
- Deterministic retry semantics
- Explicit degraded-mode behavior where needed
- No hidden dependency on manual intervention for normal operation
- Clear recovery path for partial failure

## Security and governance quality bar

Every change must respect institutional governance expectations.

### Required
- Principle of least privilege
- Internal auth between trusted services
- No secrets in code or committed configs
- Explicit model allowlisting
- Request caps for tokens, cost, timeout, or similar constraints
- Clear boundary between trusted internal callers and clients

## Documentation quality bar

Docs must sound credible, premium, and technically grounded.

### Required
- Serious, precise language
- No hype without mechanism
- Clear explanation of why a control exists
- Operationally meaningful examples
- Consistent use of repo terms

Preferred vocabulary:
- institutional-grade
- reliable
- robust
- policy-enforced
- auditable
- deterministic
- provider-agnostic
- ledger-backed
- runtime guardrails
- reserve-before-dispatch

## Code quality bar

Code must feel clean, intentional, and maintainable.

### Required
- Clear naming
- Small, focused modules
- Minimal hidden coupling
- Explicit configuration surfaces
- No dead scaffolding left unexplained
- No misleading placeholder code presented as production-ready

## Testing quality bar

Every important control path must be testable.

### Minimum expectations
- Happy path tests
- Replay and idempotency tests
- Failure-path tests
- Reconciliation tests
- Validation tests
- Schema migration sanity checks

## Deployment and ops quality bar

The repo must remain portable and operationally credible.

### Required
- Docker-first local reproducibility
- Environment-driven configuration
- Clear startup expectations
- Health or readiness endpoints where relevant
- Minimal assumptions about target environment

## Pull request quality bar

Every PR should answer these clearly:
- What institutional capability does this improve?
- What are the failure modes?
- How is idempotency or replay handled?
- How is auditability preserved?
- How is this monitored, repaired, or reconciled?
- Are docs and configs updated if behavior changed?

## Non-negotiable invariants

- Postgres is the governance system of record
- Reserve before dispatch
- Settlement must be idempotent
- Audit events must exist for material transitions
- Redis is not the ledger
- Provider access must be policy-controlled
- Runtime controls must be explicit
- Failures must be recoverable or reconcilable
- Docs must match reality
- Repo language must stay institutional-grade

## Merge rule

A change should only merge if it is **credible, deterministic, auditable, robust, and aligned with institutional-grade governance standards**.
