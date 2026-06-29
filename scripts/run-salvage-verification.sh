#!/usr/bin/env bash
# Portfolio conformance & integrity harness — L5 Institutional Self-Check Certified
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MG_INTEGRATION_TESTS=(
  tests/integration/test_ledger_hardening.py
  tests/integration/test_sidecar_admin_observability.py
  tests/integration/test_phase4_anomaly.py
  tests/integration/test_readiness.py
  tests/integration/test_fallback_limiter.py
  tests/integration/test_diagnostic_mode.py
  tests/integration/test_auth_oidc.py
  tests/integration/test_ledger_verify_chain.py
  tests/integration/test_diagnostic_write_block.py
  tests/integration/test_circuit_breaker_local_fallback.py
  tests/integration/test_admin_audit.py
  tests/integration/test_oidc_jwks_live.py
  tests/integration/test_ledger_anchor_s3.py
  tests/integration/test_micro_token_precision.py
  tests/integration/test_guardrails.py
  tests/integration/test_prometheus_scrape.py
  tests/integration/test_circuit_breaker.py
  tests/integration/test_operations_list.py
  tests/integration/test_gateway_governance.py
  tests/integration/test_gateway_openai_compat.py
  tests/integration/test_gateway_provider_router.py
  tests/integration/test_chaos_resilience.py
  tests/integration/test_property_ledger.py
  tests/integration/test_migration_invariants.py
  tests/programs/finance_ops_finals/
  tests/programs/cost_attribution_accountability/
)

echo "=========================================================================="
echo "  PORTFOLIO CONFORMANCE & INTEGRITY HARNESS (make plug)"
echo "=========================================================================="

echo "Step 1: Canonical tree footprint..."
if [[ -d cyber-governor ]]; then
  echo "FAIL: stale cyber-governor/ code tree on branch"
  exit 1
fi
if [[ -f docs/cyber-governor/spine.md ]]; then
  echo "FAIL: stale docs/cyber-governor/ content — use docs/cybersecurity-governor/"
  exit 1
fi
echo "OK    clean tree (canonical: cybersecurity-governor/)"

echo "Step 2: Port assignment invariants (governor-spine-core)..."
PYTHONPATH=governor-spine-core python3 -m spine_core.port_checks

echo "Step 3: governor-spine-core contract tests..."
PYTHONPATH=governor-spine-core python3 -m pytest governor-spine-core/tests/ -q

echo "Step 4: Cybersecurity Governor spine test matrix..."
make -C cybersecurity-governor cg-test-deps
make -C cybersecurity-governor cg-spine-test

echo "Step 5: Finance Governor spine test matrix..."
make -C finance-governor fg-spine-test

echo "Step 6: Insurance Governor spine test matrix..."
make -C insurance-governor ig-spine-test

echo "Step 7: ModelGovernor integration suite (Tier 1 parity — failures stop build)..."
pip install -q -r sidecar/requirements.txt -r reconciler/requirements.txt -r gateway/requirements.txt pytest hypothesis fakeredis 2>/dev/null || true
PYTHONPATH=governor-spine-core:. python3 -m pytest "${MG_INTEGRATION_TESTS[@]}" -q

echo "Step 8: Helm deploy kit render (CG + MG)..."
make -C cybersecurity-governor cg-helm-enterprise > /dev/null
helm template mg deploy/helm/modelgovernor --set secrets.create=true \
  --set secrets.postgresPassword=postgres > /dev/null

echo "Step 9: Portfolio maturity artifact (K2)..."
PYTHONPATH=governor-spine-core python3 -c "from spine_core.portfolio_self_check import write_portfolio_self_check; p=write_portfolio_self_check(); print('OK   wrote', p)"

echo "=========================================================================="
echo "  MATURITY PROFILE: L5 Institutional Self-Check Certified"
echo "  Portfolio readiness: governor-spine-core/docs/operational-architecture-scorecard.md"
echo "  Artifact: artifacts/portfolio_self_check.json"
echo "  This run: four-governor pytest matrices + port alignment + Helm render."
echo "  This is NOT SOC 2, ISO 27001, NHS DTAC, or third-party audit certification."
echo "  Optional live gates: make compose-smoke-cg|mg|fg|ig (requires Docker)"
echo "=========================================================================="
