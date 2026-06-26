#!/usr/bin/env bash
# Full enterprise rehearsal — stack + mock FedNow + attestation + published data room
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
IG="$ROOT/cybersecurity-governor"
PUBLISHED="$ROOT/docs/cybersecurity-governor/data-room/published"
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
    export CG_ATTESTATION_ENV="${CG_ATTESTATION_ENV:-local-embedded-rehearsal}"
    export CG_CLUSTER_ID="${CG_CLUSTER_ID:-cg-embedded-rehearsal-001}"
    export CG_CLUSTER_ATTESTATION=true
    export CG_DESIGN_PARTNER_NAME="${CG_DESIGN_PARTNER_NAME:-[REDACTED_CARRIER]}"
    python3 "$IG/scripts/attestation_embedded_rehearsal.py"
    python3 "$IG/scripts/attestation_validate.py"
    make cg-certification
    python3 "$IG/scripts/generate_design_partner_attestation.py"
    python3 "$IG/scripts/publish_data_room.py"
    echo "==> Embedded rehearsal complete — for HTTP stack run with Docker: make cg-full-rehearsal"
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
  curl -sf http://localhost:8121/readyz >/dev/null 2>&1 && \
  curl -sf http://localhost:8120/readyz >/dev/null 2>&1 && \
  curl -sf http://localhost:8103/healthz >/dev/null 2>&1 && break
  sleep 2
done
curl -sf http://localhost:8121/readyz >/dev/null
curl -sf http://localhost:8120/readyz >/dev/null
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
export CG_PLATFORM_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5434/cybersecuritygovernor
export CG_ATTESTATION_ENV=ha-rehearsal-cluster
export CG_CLUSTER_ATTESTATION=true
export CG_CLUSTER_ID=ig-rehearsal-ha-001
export CG_DESIGN_PARTNER_NAME="[REDACTED_CARRIER]"
export CG_INTERNAL_TOKENS="${CG_INTERNAL_TOKENS:-dev-cg-spine-token-change-me}"
export CG_SIDECAR_URL="http://localhost:8121"
export CG_GATEWAY_URL="http://localhost:8120"
export CG_EGRESS_GOVERN_URL="http://localhost:8103"
export CG_PLATFORM_HOST="http://localhost"
export PYTHONPATH="${IG}:${PYTHONPATH:-}"

# Apply migrations 0002-0009 if fresh postgres
for f in "$IG"/migrations/000{2,3,4,5,6,7,8,9}_*.sql; do
  [ -f "$f" ] && PGPASSWORD=postgres psql -h localhost -p 5434 -U postgres -d cybersecuritygovernor -f "$f" 2>/dev/null || true
done

echo "==> Rail smoke"
"$IG/scripts/cg-rail-smoke.sh"

echo "==> ClaimGate load"
cd "$ROOT" && make ig-claim-gate-load

echo "==> Cluster attestation (live probes)"
python3 "$IG/scripts/attestation_runner.py"
python3 "$IG/scripts/attestation_validate.py"

echo "==> Certification"
make cg-certification

echo "==> Design partner package"
python3 "$IG/scripts/generate_design_partner_attestation.py"

echo "==> Publish data room"
python3 "$IG/scripts/publish_data_room.py"

echo "==> Full rehearsal complete — see docs/cybersecurity-governor/data-room/published/"
