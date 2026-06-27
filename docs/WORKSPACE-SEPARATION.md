# Workspace separation — enterprise vs sports identity

Two commercial identities must not share one git history or deploy surface:

| Path | Identity | Contents |
|------|----------|----------|
| `~/src/hibs-racing-production/` | **Hibs Racing** (private) | `hibs_racing/`, `football/` — sports NLP / betting engineering |
| `~/src/inst-spine-core/` | **Enterprise** (acquirable) | Governor spine, Proxy-Risk, chaos tests — zero hobby baggage |

## This GitHub repo (`modelgovernor.v01`)

**Already enterprise-clean.** There is no `hibs_racing/`, `football/`, or `pyproject.toml` sports workspace entry in this clone. Separation applies to your **local mixed monorepo** on your Mac, not to this remote.

## Run the separation (local Mac)

```bash
# 1. Point at your mixed monorepo (adjust path)
export MONOREPO_PATH=~/src/your-current-monorepo-folder

# 2. Dry run first
DRY_RUN=1 bash scripts/separate-hibs-racing-identity.sh

# 3. Execute
bash scripts/separate-hibs-racing-identity.sh
```

The script:

1. Creates `~/workspace_backup_YYYYMMDD_HHMMSS.tar` (full monorepo backup)
2. Moves `hibs_racing/` and `football/` → `~/src/hibs-racing-production/`
3. `git init` in the hibs home (independent history)
4. Strips `hibs-racing` / `hibs-bet` / `football` lines from `pyproject.toml` (and other manifests if present)
5. Renames the enterprise folder → `~/src/inst-spine-core`

### Override defaults

```bash
export HIBS_HOME=~/src/hibs-racing-production   # preferred name (default)
export ENTERPRISE_NAME=inst-spine-core
```

## Verify clean enterprise state

```bash
cd ~/src/inst-spine-core
rg -i 'hibs_racing|hibs-racing|football' --glob '!docs/**'
# Expect: no matches in code; docs may mention delisted SKUs only
make demo-gold   # or your CI proof target
```

## Verify isolated sports repo

```bash
cd ~/src/hibs-racing-production
git log --oneline
git remote -v   # add private origin — never push to enterprise remote
```

## Why separate?

- **TPRM / acquirer diligence:** enterprise data room must not contain betting IP or paths
- **Compliance:** regulated infra buyers flag gambling-adjacent code in the same repo
- **Git identity:** separate `user.name` / `user.email` per repo (`git config --local`)
