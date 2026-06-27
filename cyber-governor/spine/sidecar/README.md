# Cybersecurity Governor spine sidecar (Phase 2)
# Port from modelgovernor/sidecar with finance adaptations — see docs/cyber-governor/spine-port-map.md

Modules to implement:
- crystal.py / commit_ledger.py (from ledger.py)
- security_ops.py + threat_ops.py (from finance_ops.py)
- routes_crystallize.py, routes_commit.py, routes_adjudicate.py
- security_seal.py (from ledger_seal.py)

Reference: docs/cyber-governor/spine.md
