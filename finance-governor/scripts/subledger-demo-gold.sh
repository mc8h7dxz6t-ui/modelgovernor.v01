#!/usr/bin/env bash
# SubledgerSync — demo-ready walkthrough (intercompany match-at-clear)
set -euo pipefail

SUBLEDGER="${SUBLEDGER_URL:-http://localhost:8095}"

echo "==> SubledgerSync institutional++ demo"
echo ""
echo "1) Health"
curl -sf "$SUBLEDGER/healthz"
echo ""

echo "2) Ingest UK leg"
curl -sf -X POST "$SUBLEDGER/transactions" \
  -H 'content-type: application/json' \
  -d '{"entity_id":"UK-01","counterparty_id":"US-01","amount":"10000.00","currency":"USD","value_date":"2026-06-01","reference":"interco-loan"}'
echo ""

echo "3) Match US mirror leg (FX snapshot hash sealed)"
curl -sf -X POST "$SUBLEDGER/match/run" \
  -H 'content-type: application/json' \
  -d '{"entity_id":"US-01","counterparty_id":"UK-01","amount":"10000.00","currency":"USD","value_date":"2026-06-01"}'
echo ""

echo "4) FX drift → DISCREPANCY"
curl -sf -X POST "$SUBLEDGER/match/run" \
  -H 'content-type: application/json' \
  -d '{"entity_id":"DE-01","counterparty_id":"FR-01","amount":"99999.00","currency":"USD","value_date":"2026-06-01"}'
echo ""

echo "5) Open discrepancies"
curl -sf "$SUBLEDGER/discrepancies"
echo ""
echo "subledger-demo-gold OK"
