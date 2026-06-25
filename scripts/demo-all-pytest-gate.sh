#!/usr/bin/env bash
# Assert ModelGovernor demo-all structural test gate (default: 134 certified).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

TARGET="${DEMO_ALL_TEST_TARGET:-134}"
MANIFEST="${REPO_ROOT}/scripts/demo-all-test-manifest.txt"

paths=()
while IFS= read -r line || [[ -n "$line" ]]; do
  line="${line%%#*}"
  line="$(echo "$line" | xargs)"
  [[ -z "$line" ]] && continue
  paths+=("$line")
done < "$MANIFEST"

if [[ ${#paths[@]} -eq 0 ]]; then
  paths=(tests/ tests/programs/ tests/structural/)
fi

OUT=$(python3 -m pytest "${paths[@]}" -q --tb=no 2>&1) || true
echo "$OUT"

SUMMARY=$(echo "$OUT" | rg '[0-9]+ passed.* in [0-9]' | tail -1 || true)
if [[ -z "$SUMMARY" ]]; then
  SUMMARY=$(echo "$OUT" | rg '^=+ [0-9]+ passed' | tail -1 || true)
fi
if [[ -z "$SUMMARY" ]]; then
  SUMMARY=$(echo "$OUT" | rg '[0-9]+ passed' | tail -1 || true)
fi

parse_count() {
  local label="$1"
  echo "$SUMMARY" | rg -o "[0-9]+ ${label}" | head -1 | rg -o '^[0-9]+' || echo "0"
}

PASSED=$(parse_count passed)
SKIPPED=$(parse_count skipped)
FAILED=$(parse_count failed)
ERRORS=$(parse_count error)

PASSED="${PASSED:-0}"
SKIPPED="${SKIPPED:-0}"
FAILED="${FAILED:-0}"
ERRORS="${ERRORS:-0}"

echo ""
echo "demo-all pytest gate: passed=${PASSED} skipped=${SKIPPED} failed=${FAILED} errors=${ERRORS} target=${TARGET}"

if [[ "$FAILED" != "0" || "$ERRORS" != "0" ]]; then
  echo "demo-all FAILED: ${FAILED} failed, ${ERRORS} errors" >&2
  exit 1
fi

CERTIFIED=$((PASSED + SKIPPED))
echo "demo-all certified total: ${CERTIFIED} (passed=${PASSED} + skipped=${SKIPPED})"

if [[ "$CERTIFIED" -lt "$TARGET" ]]; then
  echo "demo-all FAILED: expected >= ${TARGET} certified (passed+skipped), got ${CERTIFIED}" >&2
  exit 1
fi

echo "demo-all pytest gate OK (${PASSED} passed, ${SKIPPED} skipped, ${CERTIFIED} certified >= ${TARGET})"
exit 0
