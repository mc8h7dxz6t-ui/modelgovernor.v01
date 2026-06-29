# Threat Crystal Protocol (TCP)

**Cybersecurity Governor's unique IP** — a cross-platform primitive that no SIEM, XDR, or IdP productizes end-to-end.

> **No security surprise is allowed to authorize without a Threat Crystal.**

A **Threat Crystal** is an immutable, hash-chained snapshot of the security world **at the moment you decide to act** — identity binding, device posture, lineage parent, policy version — bound to a **Session Horizon** after which ambiguous outcomes **strand**, never guess.

---

## The three primitives

### 1. Threat Crystal

At **arm / gate** time, the platform crystallizes context:

```json
{
  "crystal_id": "tcrys_8f3a…",
  "crystal_hash": "sha256:…",
  "prev_crystal_hash": "sha256:…",
  "platform": "identity_gate",
  "risk_tier": "critical",
  "facets": {
    "user_id": "alice@corp.example",
    "device_fingerprint": "dev_fp_trusted_workstation",
    "client_ip": "10.0.1.42",
    "session_state": "AUTHORIZED",
    "policy_version": "idp-policy-v12"
  },
  "parent_crystal_id": null
}
```

| Platform | Crystallized facets |
|----------|---------------------|
| **IdentityGate** | `device_fingerprint`, `client_ip`, `user_agent`, `token_binding_hash` |
| **EgressLock** | `destination`, `byte_count`, `principal_id`, `protocol` |
| **WitnessBridge** | `source`, `event_type`, `action`, `principal_id`, `severity` |

Crystals are **hash-chained** (same machinery as ModelGovernor `ledger_seal.py`). Tamper = broken chain = SOC alarm.

### 2. Session Horizon

```
horizon_expires_at = crystallized_at + policy.commit_horizon_ms(risk_tier)
```

| Risk tier | Typical horizon | On expiry (TCP rule) |
|-----------|-----------------|----------------------|
| **Critical** (session arm, egress) | 5s – 60s | **STRAND** — never auto-authorize |
| **High** (privilege elevation) | 60s – 15m | **STRAND** — analyst adjudication |
| **Standard** (routine telemetry) | 15m – 24h | **EXPIRE** or STRAND per policy |

### 3. Crystal-bound authorize

Terminal `POST /commit` must match crystal fingerprint exactly. A hijacked session cannot commit with `session_state: STRANDED` if the crystal was armed as `AUTHORIZED`.

---

## Threat Mesh (spine-only)

```sql
INSERT INTO threat_mesh_rules (parent_platform, parent_facet_key, parent_facet_value, child_platform)
VALUES ('identity_gate', 'session_state', 'STRANDED', 'egress_lock');
```

Enforced at commit — blocked egress increments `threat_mesh_block_total`.

---

## Multi-vector resolution

| Attack step | Legacy failure | TCP resolution |
|-------------|----------------|----------------|
| Session hijack | Legit-looking login | Device fingerprint mismatch → STRANDED crystal |
| Ephemeral exploit | Function deleted | Proxy crystal at invoke — facets preserved in ledger |
| Log erasure | SOC blind | WitnessBridge critical ingest + silence detection |

---

## API (spine)

| Endpoint | Purpose |
|----------|---------|
| `POST /crystallize` | Arm threat crystal + optional action budget reserve |
| `POST /commit` | Crystal-bound terminal authorize |
| `GET /internal/crystals/{id}/reconstruct` | Forensic bundle |

Platforms use `platforms/common/spine_adapter.py` with `CG_SPINE_ENABLED=true|false`.
