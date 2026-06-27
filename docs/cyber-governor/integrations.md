# Integrations — works with most systems

Cybersecurity Governor is designed as a **standalone control plane** that integrates via HTTP JSON — no agent monoculture required.

## WitnessBridge ingest sources

`POST /ingest/{source}` accepts JSON and normalizes via `platforms/common/integrations.py`.

| Source key | Expected payload | Normalized fields |
|------------|------------------|-------------------|
| `okta` | Okta System Log event | `eventType`, `actor`, `client`, `outcome` |
| `cloudtrail` | EventBridge / CloudTrail `detail` | `eventName`, `userIdentity`, `sourceIPAddress` |
| `generic` | Any JSON | `principal_id`, `resource_id`, `action`, `severity` |

### Okta webhook example

```bash
curl -X POST http://localhost:8105/ingest/okta \
  -H 'content-type: application/json' \
  -d '{
    "eventType": "user.session.start",
    "uuid": "evt-okta-1",
    "actor": {"alternateId": "alice@corp.example"},
    "client": {"ipAddress": "10.0.1.42", "userAgent": "Mozilla/5.0"},
    "device_fingerprint": "dev_fp_trusted_workstation"
  }'
```

### CloudTrail EventBridge example

```bash
curl -X POST http://localhost:8105/ingest/cloudtrail \
  -H 'content-type: application/json' \
  -d '{
    "detail": {
      "eventName": "DeleteTrail",
      "eventID": "evt-aws-1",
      "userIdentity": {"arn": "arn:aws:iam::123:user/attacker"}
    }
  }'
```

Critical / erasure events auto-crystallize when `CG_SPINE_ENABLED=true`.

## IdentityGate

Call before token issuance or session refresh:

```bash
curl -X POST http://localhost:8103/session/arm \
  -H 'content-type: application/json' \
  -d '{
    "session_id": "sess-abc",
    "user_id": "alice@corp.example",
    "device_fingerprint": "dev_fp_trusted_workstation",
    "client_ip": "10.0.1.42"
  }'
```

Integrate at: Okta inline hook, Azure AD custom policy, API gateway auth filter.

## EgressLock

Call before data leaves the trust boundary:

```bash
curl -X POST http://localhost:8104/egress/evaluate \
  -H 'content-type: application/json' \
  -d '{
    "egress_id": "eg-1",
    "principal_id": "alice@corp.example",
    "destination": "s3://corp-backup",
    "byte_count": 1048576
  }'
```

Integrate at: S3 proxy, service mesh egress filter, CASB API.

## Spine adapter (Python)

```python
from platforms.common.spine_adapter import CommitOutcome, SpineAdapter

adapter = SpineAdapter(platform="identity_gate", spine_enabled=True)
crystal = adapter.crystallize(
    operation_id="sess-1",
    risk_tier="critical",
    facets={"session_state": "AUTHORIZED"},
    policy_id="identity-critical-us",
)
adapter.commit(CommitOutcome(
    operation_id="sess-1",
    crystal_id=crystal.crystal_id,
    facets={"session_state": "AUTHORIZED"},
    outcome="authorized",
))
```

## OpenTelemetry (future)

Security events align with ECS-like fields in crystal facets for export to existing SIEM without replacing it.
