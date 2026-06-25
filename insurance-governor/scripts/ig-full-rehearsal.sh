#!/usr/bin/env bash
# Full enterprise rehearsal — stack + mock FedNow + attestation + published data room
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
IG="$ROOT/insurance-governor"
PUBLISHED="$ROOT/docs/insurance-governor/data-room/published"
SANDBOX_PORT="${FEDNOW_SANDBOX_PORT:-8190}"

echo "==> IG Full Enterprise Rehearsal"

cd "$IG"
docker compose up -d --build --wait ig-postgres ig-redis ig-sidecar ig-gateway ig-claim-gate ig-parametric-oracle 2>/dev/null || \
  docker compose up -d --build ig-postgres ig-redis ig-sidecar ig-gateway ig-claim-gate

echo "==> Waiting for spine..."
for i in $(seq 1 60); do
  curl -sf http://localhost:8101/readyz >/dev/null 2>&1 && break
  sleep 2
done
curl -sf http://localhost:8101/readyz >/dev/null
curl -sf http://localhost:8100/readyz >/dev/null
echo "OK  spine up"

echo "==> Starting FedNow sandbox on :$SANDBOX_PORT"
python3 "$IG/scripts/mock_fednow_sandbox.py" &
SANDBOX_PID=$!
trap 'kill $SANDBOX_PID 2>/dev/null || true' EXIT
sleep 1

export FEDNOW_SANDBOX_URL="http://localhost:${SANDBOX_PORT}/"
export PAYMENT_RAIL_MODE=fednow_sandbox
export BANK_RAIL_API_TOKEN=rehearsal-sandbox-token
export IG_PLATFORM_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5434/insurancegovernor
export IG_ATTESTATION_ENV=ha-rehearsal-cluster
export IG_CLUSTER_ATTESTATION=true
export IG_CLUSTER_ID=ig-rehearsal-ha-001
export IG_DESIGN_PARTNER_NAME="[REDACTED_CARRIER]"

# Apply migrations 0002-0009 if fresh postgres
for f in "$IG"/migrations/000{2,3,4,5,6,7,8,9}_*.sql; do
  [ -f "$f" ] && PGPASSWORD=postgres psql -h localhost -p 5434 -U postgres -d insurancegovernor -f "$f" 2>/dev/null || true
done

echo "==> Rail smoke"
"$IG/scripts/ig-rail-smoke.sh"

echo "==> ClaimGate load"
cd "$ROOT" && make ig-claim-gate-load

echo "==> Cluster attestation"
python3 "$IG/scripts/attestation_runner.py"

echo "==> Certification"
make ig-certification

echo "==> Design partner package"
python3 "$IG/scripts/generate_design_partner_attestation.py"

mkdir -p "$PUBLISHED"
cp "$ROOT/artifacts/reliability/insurance-governor/cluster_attestation.json" "$PUBLISHED/" 2>/dev/null || true
cp "$ROOT/artifacts/reliability/insurance-governor/latest_attestation.json" "$PUBLISHED/certification_attestation.json" 2>/dev/null || true
cp "$ROOT/docs/insurance-governor/data-room/design-partner-package.json" "$PUBLISHED/" 2>/dev/null || true

python3 "$IG/scripts/publish_data_room.py"

echo "==> Full rehearsal complete — see docs/insurance-governor/data-room/published/"
