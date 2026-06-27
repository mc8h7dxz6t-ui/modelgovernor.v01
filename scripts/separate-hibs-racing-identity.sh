#!/usr/bin/env bash
# Separate sports-betting identity (hibs-racing) from enterprise infrastructure.
#
# Run on your Mac/Linux workstation where the mixed monorepo lives — NOT inside
# the clean modelgovernor / inst-spine-core GitHub clone (those repos have no
# sports modules).
#
# Usage:
#   export MONOREPO_PATH=~/src/your-current-monorepo-folder
#   ./scripts/separate-hibs-racing-identity.sh
#
# Dry run (prints actions only):
#   DRY_RUN=1 ./scripts/separate-hibs-racing-identity.sh
#
# Defaults:
#   HIBS_HOME=~/src/hibs-racing-production
#   ENTERPRISE_NAME=inst-spine-core

set -euo pipefail

DRY_RUN="${DRY_RUN:-0}"
MONOREPO_PATH="${MONOREPO_PATH:-}"
HIBS_HOME="${HIBS_HOME:-$HOME/src/hibs-racing-production}"
ENTERPRISE_NAME="${ENTERPRISE_NAME:-inst-spine-core}"

log() { printf '[separate] %s\n' "$*"; }
run() {
  if [[ "$DRY_RUN" == "1" ]]; then
    log "DRY_RUN: $*"
  else
    log "RUN: $*"
    eval "$@"
  fi
}

if [[ -z "$MONOREPO_PATH" ]]; then
  echo "ERROR: Set MONOREPO_PATH to your mixed monorepo root, e.g."
  echo "  export MONOREPO_PATH=~/src/your-current-monorepo-folder"
  exit 1
fi

MONOREPO_PATH="${MONOREPO_PATH/#\~/$HOME}"
MONOREPO_PATH="$(cd "$MONOREPO_PATH" && pwd)"
PARENT_DIR="$(dirname "$MONOREPO_PATH")"
CURRENT_NAME="$(basename "$MONOREPO_PATH")"
ENTERPRISE_PATH="$PARENT_DIR/$ENTERPRISE_NAME"
BACKUP_TAR="$HOME/workspace_backup_$(date +%Y%m%d_%H%M%S).tar"

HIBS_SRC="$MONOREPO_PATH/hibs_racing"
FOOTBALL_SRC="$MONOREPO_PATH/football"

log "Monorepo:      $MONOREPO_PATH"
log "Hibs home:     $HIBS_HOME"
log "Enterprise:    $ENTERPRISE_PATH (rename from $CURRENT_NAME)"
log "Backup:        $BACKUP_TAR"

if [[ ! -d "$MONOREPO_PATH" ]]; then
  echo "ERROR: MONOREPO_PATH does not exist: $MONOREPO_PATH"
  exit 1
fi

if [[ ! -d "$HIBS_SRC" && ! -d "$FOOTBALL_SRC" ]]; then
  echo "ERROR: Neither hibs_racing/ nor football/ found under $MONOREPO_PATH"
  echo "Nothing to separate. If this repo is already enterprise-only, stop here."
  exit 1
fi

if [[ -e "$ENTERPRISE_PATH" && "$MONOREPO_PATH" != "$ENTERPRISE_PATH" ]]; then
  echo "ERROR: Target enterprise path already exists: $ENTERPRISE_PATH"
  exit 1
fi

if [[ -e "$HIBS_HOME" && "$(ls -A "$HIBS_HOME" 2>/dev/null)" ]]; then
  echo "ERROR: Hibs home is not empty: $HIBS_HOME"
  exit 1
fi

# 1. Backup entire monorepo
run "tar -cf '$BACKUP_TAR' -C '$PARENT_DIR' '$CURRENT_NAME'"
log "Backup created: $BACKUP_TAR"

# 2. Create isolated hibs-racing home
run "mkdir -p '$HIBS_HOME'"

# 3. Move betting modules + init independent git repo
if [[ -d "$HIBS_SRC" ]]; then
  run "mv '$HIBS_SRC' '$HIBS_HOME/'"
fi
if [[ -d "$FOOTBALL_SRC" ]]; then
  run "mv '$FOOTBALL_SRC' '$HIBS_HOME/'"
fi

if [[ "$DRY_RUN" != "1" ]]; then
  if [[ ! -d "$HIBS_HOME/.git" ]]; then
    (
      cd "$HIBS_HOME"
      git init -b main
      git add .
      git commit -m "Initial commit: Isolated Hibs Racing identity workspace"
    )
    log "Initialized git in $HIBS_HOME"
  fi
else
  log "DRY_RUN: would git init in $HIBS_HOME"
fi

# 4. Strip betting references from enterprise manifest(s)
strip_manifest() {
  local file="$1"
  [[ -f "$file" ]] || return 0
  if [[ "$(uname)" == "Darwin" ]]; then
    run "sed -i '' '/hibs-racing/d; /hibs_racing/d; /hibs-bet/d; /football/d' '$file'"
  else
    run "sed -i '/hibs-racing/d; /hibs_racing/d; /hibs-bet/d; /football/d' '$file'"
  fi
}

strip_manifest "$MONOREPO_PATH/pyproject.toml"
strip_manifest "$MONOREPO_PATH/package.json"
strip_manifest "$MONOREPO_PATH/Cargo.toml"
strip_manifest "$MONOREPO_PATH/go.work"

# Remove empty sports dirs if move left stubs
for leftover in hibs_racing football hibs-racing; do
  if [[ -d "$MONOREPO_PATH/$leftover" ]]; then
    run "rmdir '$MONOREPO_PATH/$leftover' 2>/dev/null || rm -rf '$MONOREPO_PATH/$leftover'"
  fi
done

# Rename enterprise folder (skip if already named)
if [[ "$CURRENT_NAME" != "$ENTERPRISE_NAME" ]]; then
  run "mv '$MONOREPO_PATH' '$ENTERPRISE_PATH'"
  log "Renamed enterprise repo to $ENTERPRISE_PATH"
else
  ENTERPRISE_PATH="$MONOREPO_PATH"
  log "Enterprise folder already named $ENTERPRISE_NAME"
fi

cat <<EOF

Done.

  Sports identity:  $HIBS_HOME
  Enterprise repo:  $ENTERPRISE_PATH
  Safety backup:    $BACKUP_TAR

Next steps (manual):
  1. cd $HIBS_HOME && git remote add origin <your-private-hibs-racing-repo-url>
  2. cd $ENTERPRISE_PATH && git status   # verify no sports paths remain
  3. rg -i 'hibs|racing|football' $ENTERPRISE_PATH   # should return only docs/delist refs

EOF
