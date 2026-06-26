#!/usr/bin/env bash
# FedNow / clearinghouse sandbox rail smoke — requires BANK_RAIL_API_TOKEN + sandbox URL
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
export PYTHONPATH="${ROOT}/cybersecurity-governor:${PYTHONPATH:-}"

MODE="${PAYMENT_RAIL_MODE:-fednow_sandbox}"
echo "==> IG Rail Smoke (mode=$MODE)"

cd "$ROOT"
python3 -m pytest cybersecurity-governor/tests/test_bank_rail_sandbox.py -q -k "sandbox"

if [[ -n "${FEDNOW_SANDBOX_URL:-}" ]] && [[ -n "${BANK_RAIL_API_TOKEN:-}" ]]; then
  echo "==> Live sandbox HTTP probe"
  python3 - <<'PY'
import os
from decimal import Decimal
from platforms.common.integrations.bank_rail import dispatch_payment
from platforms.common.persistence.payment_types import PaymentInstruction, PaymentStatus

os.environ["PAYMENT_RAIL_MODE"] = "fednow_sandbox"
instr = PaymentInstruction(
    payment_id="smoke-pay-1",
    claim_id="smoke-claim",
    idempotency_key="rail-smoke-1",
    amount=Decimal("1.00"),
    currency="USD",
    payee_id="sandbox-payee",
    status=PaymentStatus.PENDING,
)
result = dispatch_payment(instr)
print({"external_ref": result.external_ref, "rail": result.rail, "status": result.status.value})
assert result.external_ref
PY
  echo "OK  live sandbox rail dispatch"
else
  echo "SKIP live sandbox (set FEDNOW_SANDBOX_URL + BANK_RAIL_API_TOKEN)"
fi

echo "==> Rail smoke complete"
