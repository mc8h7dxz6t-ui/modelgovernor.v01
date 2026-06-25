#!/usr/bin/env bash
# Cluster attestation — customer VPC / Helm staging (non-compose URLs via env)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
export IG_CLUSTER_ATTESTATION=true
export IG_ATTESTATION_ENV="${IG_ATTESTATION_ENV:-customer-vpc-staging}"
export IG_DESIGN_PARTNER_NAME="${IG_DESIGN_PARTNER_NAME:-[REDACTED_CARRIER]}"
export IG_CLUSTER_ID="${IG_CLUSTER_ID:-ig-staging-001}"

# Override for K8s in-cluster or port-forwarded staging
export IG_SIDECAR_URL="${IG_SIDECAR_URL:-http://sidecar.insurancegovernor.svc.cluster.local:8101}"
export IG_GATEWAY_URL="${IG_GATEWAY_URL:-http://gateway.insurancegovernor.svc.cluster.local:8100}"
export IG_CLAIM_GATE_URL="${IG_CLAIM_GATE_URL:-http://claim-gate.insurancegovernor.svc.cluster.local:8103}"
export IG_PLATFORM_HOST="${IG_PLATFORM_HOST:-http://claim-gate.insurancegovernor.svc.cluster.local}"

echo "==> Insurance Governor Cluster Attestation"
echo "    env=$IG_ATTESTATION_ENV cluster=$IG_CLUSTER_ID"
echo "    sidecar=$IG_SIDECAR_URL"

cd "$ROOT"
python3 insurance-governor/scripts/attestation_runner.py
make ig-certification
python3 insurance-governor/scripts/generate_design_partner_attestation.py
echo "==> Cluster attestation published to artifacts/reliability/insurance-governor/cluster_attestation.json"
