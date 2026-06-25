#!/usr/bin/env bash
# Full enterprise rehearsal — stack + mock FedNow + attestation + published data room
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
IG="$ROOT/insurance-governor"
PUBLISHED="$ROOT/docs/insurance-governor/data-room/published"
SANDBOX_PORT="${FEDNOW_SANDBOX_PORT:-8190}"

echo "==> IG Full Enterprise Rehearsal"

cd "$IG"
DOCKER="${DOCKER:-docker}"
if ! $DOCKER info >/dev/null 2>&1; then
  if sudo $DOCKER info >/dev/null 2>&1; then
    DOCKER="sudo docker"
  else
    echo "WARN  Docker unavailable — falling back to embedded attestation rehearsal"
    cd "$ROOT"
    export IG_ATTESTATION_ENV="${IG_ATTESTATION_ENV:-local-embedded-rehearsal}"
    export IG_CLUSTER_ID="${IG_CLUSTER_ID:-ig-embedded-rehearsal-001}"
    export IG_CLUSTER_ATTESTATION=true
    export IG_DESIGN_PARTNER_NAME="${IG_DESIGN_PARTNER_NAME:-[REDACTED_CARRIER]}"
    python3 "$IG/scripts/attestation_embedded_rehearsal.py"
    python3 "$IG/scripts/attestation_validate.py"
    make ig-certification
    python3 "$IG/scripts/generate_design_partner_attestation.py"
    python3 "$IG/scripts/publish_data_room.py"
    echo "==> Embedded rehearsal complete — for HTTP stack run with Docker: make ig-full-rehearsal"
    exit 0
  fi
fi

$DOCKER compose up -d --build \
  ig-postgres ig-redis ig-sidecar ig-gateway ig-reconciler \
  ig-claim-gate ig-bind-authority ig-parametric-oracle ig-zk-claim-audit \
  ig-spatial-twin ig-battery-liability ig-subrogation-graph \
  ig-indemnity-pay-gate ig-model-risk-freeze ig-underwriting-govern ig-reserve-reconcile

echo "==> Waiting for spine + ClaimGate..."
for i in $(seq 1 90); do
  curl -sf http://localhost:8101/readyz >/dev/null 2>&1 && \
  curl -sf http://localhost:8100/readyz >/dev/null 2>&1 && \
  curl -sf http://localhost:8103/healthz >/dev/null 2>&1 && break
  sleep 2
done
curl -sf http://localhost:8101/readyz >/dev/null
curl -sf http://localhost:8100/readyz >/dev/null
curl -sf http://localhost:8103/healthz >/dev/null
echo "OK  spine + ClaimGate up"

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
export IG_INTERNAL_TOKENS="${IG_INTERNAL_TOKENS:-dev-ig-spine-token-change-me}"
export IG_SIDECAR_URL="http://localhost:8101"
export IG_GATEWAY_URL="http://localhost:8100"
export IG_CLAIM_GATE_URL="http://localhost:8103"
export IG_PLATFORM_HOST="http://localhost"
export PYTHONPATH="${IG}:${PYTHONPATH:-}"

# Apply migrations 0002-0009 if fresh postgres
for f in "$IG"/migrations/000{2,3,4,5,6,7,8,9}_*.sql; do
  [ -f "$f" ] && PGPASSWORD=postgres psql -h localhost -p 5434 -U postgres -d insurancegovernor -f "$f" 2>/dev/null || true
done

echo "==> Rail smoke"
"$IG/scripts/ig-rail-smoke.sh"

echo "==> ClaimGate load"
cd "$ROOT" && make ig-claim-gate-load

echo "==> Cluster attestation (live probes)"
python3 "$IG/scripts/attestation_runner.py"
python3 "$IG/scripts/attestation_validate.py"

echo "==> Certification"
make ig-certification

echo "==> Design partner package"
python3 "$IG/scripts/generate_design_partner_attestation.py"

echo "==> Publish data room"
python3 "$IG/scripts/publish_data_room.py"

echo "==> Full rehearsal complete — see docs/insurance-governor/data-room/published/"
