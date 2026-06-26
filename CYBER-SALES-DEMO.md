# Cybersecurity Governor — Sales Demo

**Plug-and-play institutional++ security walkthrough. No API keys. No cloud. ~7 minutes.**

Closes **The Shadow Gap** live: session hijack → log erasure → blocked exfil — with Threat Crystal Protocol, Threat Mesh, and hash-chain verification.

## Prerequisites

```bash
make demo-prereqs-install   # Docker + Compose + curl + make (once)
```

## Run

```bash
make cg-stack-up
make cg-security-demo
```

Or step-by-step:

```bash
make cg-spine-test          # 19+ unit tests
make threat-crystal-demo    # multi-vector scripted attack
make lineage-ingest-demo    # Falco/Tetragon structural DAG
```

## Talk track (7 minutes)

### 1. The problem (30s)

Multi-vector attacks exploit three gaps incumbents cannot close:

- **Time-skew** — logs arrive out of true order
- **Ephemeral erasure** — serverless assets vanish before IR
- **Log mutation** — admins delete audit trails

SIEM correlates guesses. **Cybersecurity Governor binds authorization to Threat Crystals.**

### 2. Trusted session arm (90s)

```bash
curl -X POST http://localhost:8103/session/arm \
  -H 'content-type: application/json' \
  -d '{"session_id":"demo","user_id":"alice@corp.example","device_fingerprint":"dev_fp_trusted_workstation","client_ip":"10.0.1.42"}'
```

→ `AUTHORIZED` + `tcrys_*` crystal on spine.

### 3. Multi-vector attack live (3 min) — **the money shot**

**Session hijack:**

```bash
curl -X POST http://localhost:8103/session/arm \
  -d '{"session_id":"hijack","user_id":"alice@corp.example","device_fingerprint":"attacker_device","client_ip":"203.0.113.9"}'
```

→ `STRANDED` — device binding mismatch. No silent trust.

**Log erasure:**

```bash
curl -X POST http://localhost:8105/ingest/cloudtrail \
  -d '{"detail":{"eventName":"DeleteTrail","eventID":"evt-1","userIdentity":{"arn":"arn:aws:iam::123:user/attacker"}}}'
```

→ Critical event witnessed + crystallized.

**Egress attempt while STRANDED (Threat Mesh):**

Identity STRANDED blocks egress commit via mesh rule `identity_gate.session_state=STRANDED → egress_lock`.

```bash
curl -X POST http://localhost:8104/egress/evaluate \
  -d '{"egress_id":"ex-1","principal_id":"alice@corp.example","destination":"evil-exfil.example","byte_count":99999999}'
```

→ `BLOCKED` before bytes leave.

### 4. Kernel lineage (60s)

```bash
curl -X POST http://localhost:8106/ingest/falco \
  -d '{"rule":"Terminal shell in container","priority":"Critical","output_fields":{"proc.name":"bash","proc.pname":"sh","user.name":"root"}}'
```

→ Structural DAG edge + critical crystal. Works with **existing Falco/Tetragon** — no rip-and-replace.

### 5. Forensic proof (90s)

```bash
curl -H 'x-internal-token: dev-cg-spine-token-change-me' \
  http://localhost:8101/internal/security/verify-chain

curl -H 'x-internal-token: dev-cg-spine-token-change-me' \
  -X POST http://localhost:8101/internal/security/anchor-head
```

→ Hash chain valid. Head recorded for witness quorum (S3 Object Lock in production).

### 6. Production flip chart (30s)

| Capability | Production |
|------------|------------|
| Witness quorum | S3 Object Lock bucket (`deploy/infra/aws/security-anchor-bucket.yaml`) |
| K8s | `kubectl apply -k cyber-governor/deploy/base/` |
| Strand egress | NetworkPolicy `strand-egress-deny-template` |
| Standalone | `CG_SPINE_ENABLED=false` per platform |

## Teardown

```bash
make cg-stack-down
```

## Docs

| Doc | Use |
|-----|-----|
| [docs/cyber-governor/threat-crystal-protocol.md](docs/cyber-governor/threat-crystal-protocol.md) | Unique IP |
| [docs/cyber-governor/integrations.md](docs/cyber-governor/integrations.md) | Okta / CloudTrail / Falco |
| [docs/cyber-governor/institutional-gold-standard.md](docs/cyber-governor/institutional-gold-standard.md) | RFP / reliability |
| [cyber-governor/deploy/README.md](cyber-governor/deploy/README.md) | K8s + S3 witness |

## Positioning line

> EDR tells you what ran. SIEM guesses if alerts relate. **Cybersecurity Governor** proves under which governed conditions identity and egress were authorized — and **strands the session** when proof breaks, **before exfil commits**.
