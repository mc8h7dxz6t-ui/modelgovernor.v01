# Security Enforcement Mesh

The Security Enforcement Mesh is Cybersecurity Governor's primary **runtime** differentiator vs GRC suites and SIEM platforms that operate post-hoc.

## How it works

When platform A commits a crystal with a blocking facet value, platform B's commits are rejected at the spine **before** side effects execute.

Rules are stored in `crystal_mesh_rules` (seeded in migration `0004_cg_platforms_mesh.sql`):

| Parent platform | Facet | Value | Blocks |
|-----------------|-------|-------|--------|
| posture_reconcile | match_state | DRIFT | egress_govern, incident_response_gate |
| threat_proxy | threat_decision | BLOCKED | egress_govern, incident_response_gate |
| identity_govern | identity_decision | VIOLATION | incident_response_gate, egress_govern |
| egress_govern | egress_decision | DENIED | incident_response_gate |

## Why rivals can't match this easily

| Approach | Limitation |
|----------|------------|
| SIEM correlation rules | Minutes-to-hours latency; cannot block in-flight commits |
| GRC policy workflows | Human approval loops; not wired to runtime dispatch |
| CNAPP posture scores | Alerts only; no commit authority revocation |
| Istio NetworkPolicy | L4/L7 transport; no semantic threat/posture facets |

CG binds **semantic security state** to the CCP spine so mesh evaluation is sub-second and examiner-auditable via hash chain.

## Verification

```bash
pytest cybersecurity-governor/tests/test_security_mesh.py -q
```

## Operator tuning

Add rules via SQL or admin API (future). Each rule requires `parent_platform`, `parent_facet_key`, `parent_facet_value`, and `child_platform`.
