"""ISO 20022 / SWIFT message adapter — format + semantic intent extraction."""
from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


@dataclass(frozen=True)
class Iso20022WireIntent:
    wire_id: str
    beneficiary_name: str
    beneficiary_account: str
    amount: Decimal
    currency: str
    reference: str
    message_type: str = "pacs.008"


def parse_pacs008_stub(xml_or_json: str) -> Iso20022WireIntent:
    """Extract beneficiary intent from ISO 20022 pacs.008 stub (XML or tagged text)."""
    def _tag(name: str) -> str | None:
        m = re.search(rf"<{name}[^>]*>([^<]+)</{name}>", xml_or_json, re.I)
        if m:
            return m.group(1).strip()
        m = re.search(rf"{name}=([^\s;]+)", xml_or_json, re.I)
        return m.group(1).strip() if m else None

    wire_id = _tag("EndToEndId") or _tag("wire_id") or "unknown"
    name = _tag("Nm") or _tag("beneficiary_name") or ""
    account = _tag("IBAN") or _tag("beneficiary_account") or ""
    amount_raw = _tag("InstdAmt") or _tag("amount") or "0"
    currency = _tag("Ccy") or _tag("currency") or "USD"
    reference = _tag("Ustrd") or _tag("reference") or ""

    try:
        amount = Decimal(amount_raw)
    except InvalidOperation as exc:
        raise ValueError("invalid ISO 20022 amount") from exc

    return Iso20022WireIntent(
        wire_id=wire_id,
        beneficiary_name=name,
        beneficiary_account=account,
        amount=amount,
        currency=currency,
        reference=reference,
    )
