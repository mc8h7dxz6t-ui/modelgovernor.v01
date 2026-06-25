from decimal import Decimal

from platforms.common.integrations.fnol_adapter import normalize_fnol


def test_guidewire_fnol_normalization():
    fnol = normalize_fnol(
        "guidewire",
        {
            "claim": {
                "claimNumber": "GW-1001",
                "policyNumber": "POL-AUTO-001",
                "lossDate": "2025-05-15",
                "reportedAmount": "12000.00",
                "claimantId": "clm-99",
                "id": "evt-gw-1",
            }
        },
    )
    assert fnol.vendor == "guidewire"
    assert fnol.claim_id == "GW-1001"
    assert fnol.reported_amount == Decimal("12000.00")


def test_snapsheet_fnol_normalization():
    fnol = normalize_fnol(
        "snapsheet",
        {
            "data": {
                "claim_number": "SS-2002",
                "policy_number": "POL-PROP-001",
                "date_of_loss": "2025-04-01",
                "reserve_amount": "50000",
                "claimant_id": "ss-clm",
                "id": "evt-ss-1",
            }
        },
    )
    assert fnol.vendor == "snapsheet"
    assert fnol.policy_number == "POL-PROP-001"


def test_majesco_fnol_normalization():
    fnol = normalize_fnol(
        "majesco",
        {
            "claimEvent": {
                "claimRef": "MJ-3003",
                "policyRef": "POL-PROP-001",
                "incidentDate": "2025-03-20",
                "estimatedLoss": "7500.00",
                "insuredId": "ins-1",
                "eventId": "evt-mj-1",
            }
        },
    )
    assert fnol.vendor == "majesco"
    assert fnol.claim_id == "MJ-3003"


def test_unsupported_vendor_raises():
    try:
        normalize_fnol("unknown_vendor", {})
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "unsupported" in str(exc).lower()


def test_acturis_uk_fnol():
    fnol = normalize_fnol(
        "acturis",
        {
            "notification": {
                "claimReference": "ACT-UK-100",
                "policyReference": "POL-MOTOR-UK-001",
                "dateOfLoss": "2025-04-10",
                "estimatedAmount": "6200.50",
                "currencyCode": "GBP",
                "notificationId": "act-evt-100",
            }
        },
    )
    assert fnol.vendor == "acturis"
    assert fnol.currency == "GBP"
    assert fnol.policy_number == "POL-MOTOR-UK-001"


def test_ssp_uk_fnol():
    fnol = normalize_fnol(
        "ssp",
        {
            "claim": {
                "claimNumber": "SSP-UK-200",
                "policyNumber": "POL-MOTOR-UK-001",
                "dateOfLoss": "2025-03-15",
                "initialReserve": "3100",
                "currency": "GBP",
                "eventId": "ssp-evt-1",
            }
        },
    )
    assert fnol.vendor == "ssp"
    assert fnol.claim_id == "SSP-UK-200"
