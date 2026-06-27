# Cybersecurity Governor — spine

Shared control plane (ports **8120–8122**). Platform wedges work standalone via `CG_SPINE_ENABLED=false`.

| Service | Port | Role |
|---------|------|------|
| cg-gateway | 8120 | `/governed/commit` orchestration |
| cg-sidecar | 8121 | TCP crystallize/commit, security escrow, `security_ops` |
| cg-reconciler | 8122 | Horizon sweep, strand, post-sweep audit |

Compose and Helm must match Dockerfile listen ports (8120/8121/8122).
