#!/usr/bin/env bash
# Cluster attestation — customer VPC / Helm staging (non-compose URLs via env)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
export CG_CLUSTER_ATTESTATION=true
export CG_ATTESTATION_ENV="${CG_ATTESTATION_ENV:-customer-vpc-staging}"
export CG_DESIGN_PARTNER_NAME="${CG_DESIGN_PARTNER_NAME:-[REDACTED_CARRIER]}"
export CG_CLUSTER_ID="${CG_CLUSTER_ID:-cg-staging-001}"

# Override for K8s in-cluster or port-forwarded staging
export CG_SIDECAR_URL="${CG_SIDECAR_URL:-http://sidecar.cybersecuritygovernor.svc.cluster.local:8121}"
export CG_GATEWAY_URL="${CG_GATEWAY_URL:-http://gateway.cybersecuritygovernor.svc.cluster.local:8120}"
export CG_EGRESS_GOVERN_URL="${CG_EGRESS_GOVERN_URL:-http://claim-gate.cybersecuritygovernor.svc.cluster.local:8103}"
export CG_PLATFORM_HOST="${CG_PLATFORM_HOST:-http://claim-gate.cybersecuritygovernor.svc.cluster.local}"

echo "==> Cybersecurity Governor Cluster Attestation"
echo "    env=$CG_ATTESTATION_ENV cluster=$CG_CLUSTER_ID"
echo "    sidecar=$CG_SIDECAR_URL"

cd "$ROOT"
python3 cybersecurity-governor/scripts/attestation_runner.py
make cg-certification
python3 cybersecurity-governor/scripts/generate_design_partner_attestation.py
echo "==> Cluster attestation published to artifacts/reliability/cybersecurity-governor/cluster_attestation.json"
