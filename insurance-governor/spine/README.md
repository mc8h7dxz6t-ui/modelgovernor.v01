# Insurance Governor Spine

Optional shared control plane (ports **8100–8102**). Platforms work without it.

| Service | Port | Role |
|---------|------|------|
| ig-gateway | 8100 | `/governed/commit` orchestration |
| ig-sidecar | 8101 | CCP crystallize/commit, claim escrow, claim_ops |
| ig-reconciler | 8102 | Horizon sweep, strand, post-sweep audit |

## APIs (sidecar, internal token)

- `POST /crystallize` — create Governance Crystal + optional reserve hold
- `POST /commit` — crystal-bound terminal outcome
- `GET /internal/claims/verify-chain` — tamper detection (422 on break)
- `GET /internal/crystals/{id}/reconstruct` — examiner export

## Institutional++ parity with ModelGovernor

- Postgres authoritative; Redis diagnostic flag only
- Sealed hash chain on all claim events (including sweeps)
- Reconciler halts in diagnostic mode
- `claim_ops` session-wide invariant probes after sweep
