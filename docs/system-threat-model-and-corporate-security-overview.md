# System Threat Model & Corporate Security Overview

## Purpose

This document provides a questionnaire-ready security overview for
`modelgovernor.v01`.  It combines a system threat model with the operational and
security controls visible in the repository, while clearly separating
repository-backed facts from deployment-specific responsibilities.

## Scope and evidence boundary

This overview is grounded in the repository's current architecture:

- gateway-mediated governed request flow
- sidecar-enforced policy, ledger mutation, and admin controls
- Postgres as the authoritative ledger and audit system of record
- Redis as a volatile runtime-guardrail store only
- reconciler-based expiry and stranded-hold repair
- Prometheus-facing health, readiness, and invariant metrics

It is not a claim of certification, attestation, or hosted-service compliance.
Operators still need to answer environment-specific questions about cloud
provider selection, key management, TLS termination, backup retention, and
incident-response staffing.

## Security objectives

- prevent unauthorized spend or ledger mutation
- preserve auditable and deterministic financial state transitions
- prevent ungoverned provider access from application workloads
- protect internal administrative surfaces
- preserve availability of the governance path during component failure
- keep secrets and trust anchors outside repository state

## System overview

Core components:

- **Client / workload caller** submits OpenAI-compatible traffic
- **Gateway** normalizes and routes provider traffic
- **Sidecar** enforces policy, reserve, settle, reconcile, and admin workflows
- **Postgres** stores wallets, reservations, audit events, and orchestration
  decision history
- **Redis** stores short-lived runtime guardrail state
- **Reconciler** repairs stale reservations and stranded operations
- **Providers** receive upstream model requests only after reservation commit

## Data classes

- **control-plane metadata:** tenant, trace, model, idempotency, policy context
- **financial data:** wallet balances, reservations, settlements, refunds,
  drift, audit events
- **runtime guardrail data:** concurrency counters, trace depth, rate windows
- **administrative records:** audit log entries, correction actions, unlocks
- **observability data:** metrics, health states, alerting signals

## High-level data flow

### Governed inference path

1. Client sends request to the gateway.
2. Gateway forwards governance metadata to the sidecar.
3. Sidecar authenticates the internal caller and validates policy.
4. Sidecar checks runtime guardrails in Redis when enabled.
5. Sidecar reserves spend inside a Postgres transaction.
6. Gateway dispatches to a provider only after reservation success.
7. Settlement returns to the sidecar, which appends terminal ledger and audit
   events.

### Administrative path

1. Trusted operator or trusted internal service calls the sidecar admin route.
2. Sidecar enforces `X-Internal-Token`.
3. Sidecar reads or appends authoritative records in Postgres.
4. Administrative action is preserved in the audit log.

### Reconciliation path

1. Reconciler wakes on schedule.
2. Reconciler claims eligible rows through database locking semantics.
3. Reconciler expires safe holds or marks ambiguous rows as stranded.
4. Repair activity is recorded as append-only state transitions.

### Observability path

1. Prometheus scrapes `/metrics`.
2. Operators monitor alerts for reserve denials, drift enforcement, stranded
   growth, and negative-wallet anomalies.
3. `/healthz` and `/readyz` provide liveness and traffic-gating signals.

## Trust boundaries

| Boundary | Risk focus | Primary controls |
|---|---|---|
| Client to gateway | malformed or abusive inbound traffic | ingress controls, model allowlists, gateway normalization, request caps |
| Gateway to sidecar | forged internal calls, policy bypass | `X-Internal-Token`, private networking, least-privilege routing |
| Sidecar to Postgres | unauthorized ledger mutation | transactional writes, exact-decimal accounting, append-only audit events |
| Sidecar to Redis | misuse of volatile state as source of truth | Redis limited to non-authoritative guardrails |
| Reconciler to Postgres | unsafe repair or duplicate expiry | deterministic sweep logic, lock-based claiming, append-only repair events |
| Sidecar admin routes | privileged misuse or network exposure | internal-only routing, token auth, audit log capture |
| Gateway to provider | direct spend without governance | reserve-before-dispatch sequencing, provider attempts tied to logical operation |
| Metrics endpoints | information leakage or blind spots | internal scraping, alerting rules, environment-specific access restriction |

## Threat model

The platform threat model is centered on governance bypass, unauthorized spend,
privileged misuse, secrets exposure, and availability loss.

### Key threat scenarios and mitigations

| Threat | Likely impact | Mitigation controls |
|---|---|---|
| Direct provider egress bypasses governance | unbounded spend, missing audit trail | require provider access through gateway; keep sidecar as policy gate; restrict network egress |
| Forged internal call to sidecar | unauthorized reserve/settle/admin action | `X-Internal-Token`, private service exposure, NetworkPolicy, secret rotation |
| Duplicate or replayed settlement | double charge, incorrect wallet balance | idempotency keys, row locking, explicit terminal-state validation |
| Concurrent reservations oversubscribe a trace cap | trace-budget breach | authoritative `trace_budget_state` update in a Postgres transaction |
| Redis outage or corruption affects spend truth | false financial state | Redis not used as ledger; Postgres remains authoritative |
| Reconciler races refund the same row twice | negative balances or inconsistent repair | PostgreSQL locking semantics and deterministic reason-coded repair |
| Admin route abuse | hidden manual manipulation | internal auth, audit logging, internal-only exposure, least-privilege admin access |
| Secret leakage from manifests or code | system compromise | external secret management, no production secrets in repo, scoped service accounts |
| Excessive scale overwhelms database path | availability incident | HPA ceilings, small app pools, PgBouncer/RDS Proxy, readiness gates |
| Metrics or readiness blind spots | slow incident detection | `/metrics`, `/healthz`, `/readyz`, Prometheus rules, rollout gates |

## Security control domains

### Identity and access control

- privileged routes use internal token authentication
- Kubernetes service accounts should be separated by component
- admin endpoints should remain on trusted internal networks only
- production clusters should add RBAC and secret-manager-backed credential
  rotation

### Secrets handling

- secrets are expected to come from an external manager
- production values should not be committed into manifests or repository files
- minimum sensitive values include database credentials, Redis credentials, and
  sidecar internal tokens

### Data integrity

- Postgres is the only financial source of truth
- monetary paths use deterministic state transitions
- audit events preserve historical meaning rather than overwriting terminal state
- reconciliation is append-only and repair-oriented

### Network security

- private connectivity is expected between gateway and sidecar
- sidecar should not be publicly reachable for admin workflows
- default-deny network policies are recommended for Kubernetes deployments
- provider egress should be explicitly restricted to approved endpoints

### Container and workload hardening

- non-root execution
- read-only root filesystem
- no privilege escalation
- explicit resource bounds
- readiness and liveness probes on request-path workloads

### Logging, audit, and monitoring

- append-only ledger and admin audit records support investigation
- Prometheus metrics expose invariant and health signals
- alert rules cover reserve denials, drift enforcement, stranded growth, and
  negative-wallet events
- operational runbooks define recovery expectations

### Resilience and recovery

- readiness gates protect rollouts
- reconciler provides deterministic stale-work cleanup
- failover guidance exists for Postgres and Redis recovery paths
- backup, restore, and retention settings remain deployment-specific

## Shared responsibility model

### Repository-provided controls

- control-plane architecture and trust boundaries
- internal-auth-protected admin surfaces
- health, readiness, and metrics endpoints
- audit-oriented ledger model and reconciliation behavior
- CI validation, migration checks, and deployment rendering validation
- baseline Kubernetes manifests and operator runbook

### Operator-supplied controls

- TLS certificates and ingress security policy
- managed Postgres and Redis hardening
- secret-manager integration and rotation cadence
- backup, restore, retention, and disaster-recovery objectives
- SSO, MFA, bastion, and human-access approval workflows
- vulnerability scanning, patch windows, and incident communications

## Corporate security overview

For standard questionnaires, the supported answer is:

- **Hosting model:** self-hosted or operator-hosted control plane on Kubernetes
  or equivalent container platform
- **Primary system of record:** PostgreSQL ledger and audit database
- **Administrative protection:** internal token authentication plus internal
  network restriction
- **Monitoring:** Prometheus scraping, alert rules, readiness and liveness
  probes, operator runbooks
- **Secrets posture:** externally managed secrets; no production secrets in
  repository state
- **Change safety:** CI-backed tests, compile checks, migration parsing, manifest
  rendering validation
- **Recovery posture:** reconciler-based repair, runbook-driven failover and
  restart procedures, deployment-specific backup strategy

Where a questionnaire asks for certifications, named subprocessors, staff
screening, or corporate policy attestations, those answers must come from the
actual operating organization rather than from the repository alone.

## Residual risks and assumptions

- the current `/readyz` endpoint is process-level readiness, not a deep
  dependency health check
- provider-side outages or billing discrepancies still require operational
  reconciliation
- hosted-environment controls such as WAF, TLS policy, MFA, and SIEM integration
  are outside repository scope and must be supplied by the operator

## Questionnaire-ready conclusion

`modelgovernor.v01` presents a strong security architecture for governed AI
spend control: policy enforcement is separated from provider routing, financial
state is ledger-backed and auditable, privileged repair paths are internal-only,
and runtime health and invariant signals are observable.  The remaining
security-questionnaire answers are primarily deployment-organization concerns
rather than gaps in the repository's control-plane design.
