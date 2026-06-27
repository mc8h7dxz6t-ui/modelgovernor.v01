# Workspace separation — Hibs Racing vs Model Governor

Two repos, two identities. Do not mix sports betting engineering with governor infrastructure.

| Path | Identity | What lives here |
|------|----------|-----------------|
| `~/src/hibs-racing/` | **Hibs Racing** (private) | `hibs_racing/`, `football/` — sports NLP / betting |
| `~/src/modelgovernor/` | **Model Governor** (enterprise) | MG, FG, CG governors — sidecar, gateway, reconciler, chaos tests |

**Not** `inst-spine-core`. Governors stay under **modelgovernor**.

## This GitHub repo (`modelgovernor.v01`)

Already governor-only. No `hibs_racing/` or `football/` here. If your Mac still has a **mixed** monorepo with both, run the separation script locally.

## Run on your Mac

```bash
export MONOREPO_PATH=~/src/your-mixed-monorepo   # folder that still has both

DRY_RUN=1 bash scripts/separate-hibs-racing-identity.sh   # preview
bash scripts/separate-hibs-racing-identity.sh               # execute
```

The script:

1. Backs up the mixed repo → `~/workspace_backup_*.tar`
2. Moves `hibs_racing/` + `football/` → `~/src/hibs-racing/`
3. `git init` in hibs-racing (fresh sports history)
4. Strips sports lines from `pyproject.toml` etc. in the governor tree
5. Renames the remaining folder → `~/src/modelgovernor` (if not already named)

### Defaults (override if needed)

```bash
export HIBS_HOME=~/src/hibs-racing
export ENTERPRISE_NAME=modelgovernor
```

## Verify

```bash
# Governors — no sports code
cd ~/src/modelgovernor
rg -i 'hibs_racing|football' --glob '!docs/**'
make demo-gold

# Sports — separate remote, separate git identity
cd ~/src/hibs-racing
git remote add origin <your-private-repo>
git config user.name "..."    # sports identity, not enterprise
```

## Why separate?

- Acquirer / TPRM diligence: governor data room must not contain betting paths
- Compliance: regulated buyers flag gambling-adjacent code in infra repos
- Git: independent history and remotes per commercial identity
