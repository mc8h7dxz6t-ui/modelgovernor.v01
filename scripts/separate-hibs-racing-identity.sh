#!/usr/bin/env bash
# Separate sports identity (hibs-racing) from governor platform (modelgovernor).
#
# Two repos, two identities:
#   ~/src/hibs-racing/     — sports NLP / betting (private)
#   ~/src/modelgovernor/   — MG / FG / CG governors (enterprise, acquirable)
#
# Run on your Mac/Linux workstation where a MIXED monorepo still contains both.
# The GitHub clone modelgovernor.v01 is already governor-only (no sports modules).
#
# Usage:
#   export MONOREPO_PATH=~/src/your-mixed-monorepo
#   ./scripts/separate-hibs-racing-identity.sh
#
# Dry run:
#   DRY_RUN=1 ./scripts/separate-hibs-racing-identity.sh
#
# Defaults:
#   HIBS_HOME=~/src/hibs-racing
#   ENTERPRISE_NAME=modelgovernor

set -euo pipefail

DRY_RUN="${DRY_RUN:-0}"
MONOREPO_PATH="${MONOREPO_PATH:-}"
HIBS_HOME="${HIBS_HOME:-$HOME/src/hibs-racing}"
ENTERPRISE_NAME="${ENTERPRISE_NAME:-modelgovernor}"

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
  echo "  export MONOREPO_PATH=~/src/your-mixed-monorepo"
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

log "Mixed monorepo: $MONOREPO_PATH"
log "Hibs Racing:    $HIBS_HOME"
log "Model Governor: $ENTERPRISE_PATH"
log "Backup:         $BACKUP_TAR"

if [[ ! -d "$MONOREPO_PATH" ]]; then
  echo "ERROR: MONOREPO_PATH does not exist: $MONOREPO_PATH"
  exit 1
fi

if [[ ! -d "$HIBS_SRC" && ! -d "$FOOTBALL_SRC" ]]; then
  echo "ERROR: Neither hibs_racing/ nor football/ found under $MONOREPO_PATH"
  echo ""
  echo "If governors already live in ~/src/modelgovernor with no sports folders,"
  echo "you are done — nothing to separate."
  exit 1
fi

if [[ -e "$ENTERPRISE_PATH" && "$MONOREPO_PATH" != "$ENTERPRISE_PATH" ]]; then
  echo "ERROR: Target governor path already exists: $ENTERPRISE_PATH"
  echo "Move or rename it first, or set ENTERPRISE_NAME to something else."
  exit 1
fi

if [[ -e "$HIBS_HOME" && "$(ls -A "$HIBS_HOME" 2>/dev/null)" ]]; then
  echo "ERROR: Hibs Racing home is not empty: $HIBS_HOME"
  exit 1
fi

# 1. Backup entire monorepo
run "tar -cf '$BACKUP_TAR' -C '$PARENT_DIR' '$CURRENT_NAME'"
log "Backup created: $BACKUP_TAR"

# 2. Create isolated hibs-racing home
run "mkdir -p '$HIBS_HOME'"

# 3. Move sports modules + init independent git repo
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
      git commit -m "Initial commit: Hibs Racing — isolated sports identity"
    )
    log "Initialized git in $HIBS_HOME"
  fi
else
  log "DRY_RUN: would git init in $HIBS_HOME"
fi

# 4. Strip sports references from governor manifests (keep governor packages)
strip_manifest() {
  local file="$1"
  [[ -f "$file" ]] || return 0
  if [[ "$(uname)" == "Darwin" ]]; then
    run "sed -i '' '/hibs-racing/d; /hibs_racing/d; /hibs-bet/d; /\\/football/d' '$file'"
  else
    run "sed -i '/hibs-racing/d; /hibs_racing/d; /hibs-bet/d; /\\/football/d' '$file'"
  fi
}

strip_manifest "$MONOREPO_PATH/pyproject.toml"
strip_manifest "$MONOREPO_PATH/package.json"
strip_manifest "$MONOREPO_PATH/Cargo.toml"
strip_manifest "$MONOREPO_PATH/go.work"

for leftover in hibs_racing football hibs-racing; do
  if [[ -d "$MONOREPO_PATH/$leftover" ]]; then
    run "rmdir '$MONOREPO_PATH/$leftover' 2>/dev/null || rm -rf '$MONOREPO_PATH/$leftover'"
  fi
done

# 5. Rename enterprise folder to modelgovernor (governors only)
if [[ "$CURRENT_NAME" != "$ENTERPRISE_NAME" ]]; then
  run "mv '$MONOREPO_PATH' '$ENTERPRISE_PATH'"
  log "Renamed governor repo to $ENTERPRISE_PATH"
else
  ENTERPRISE_PATH="$MONOREPO_PATH"
  log "Governor folder already named $ENTERPRISE_NAME"
fi

cat <<EOF

Done — two identities:

  Hibs Racing (sports):     $HIBS_HOME
  Model Governor (MG/FG/CG): $ENTERPRISE_PATH
  Safety backup:            $BACKUP_TAR

Next steps:
  1. cd $HIBS_HOME && git remote add origin <private-hibs-racing-repo>
  2. cd $ENTERPRISE_PATH && git status
  3. rg -i 'hibs_racing|football' $ENTERPRISE_PATH --glob '!docs/**'  # expect empty

EOF
