"""FNOL integration adapters — normalize core-system webhooks into ClaimGate facets."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class NormalizedFnol:
    vendor: str
    claim_id: str
    policy_number: str
    loss_date: date
    reported_amount: Decimal
    currency: str
    loss_type: str
    claimant_id: str
    raw_vendor_id: str
    fraud_signals: list[str]


def _parse_date(value: str) -> date:
    return date.fromisoformat(value[:10])


def from_guidewire(payload: dict[str, Any]) -> NormalizedFnol:
    """Guidewire ClaimCenter FNOL webhook shape (simplified)."""
    claim = payload.get("claim", payload)
    return NormalizedFnol(
        vendor="guidewire",
        claim_id=str(claim.get("claimNumber") or claim.get("id")),
        policy_number=str(claim.get("policyNumber", "POL-AUTO-001")),
        loss_date=_parse_date(str(claim.get("lossDate", date.today().isoformat()))),
        reported_amount=Decimal(str(claim.get("reportedAmount", "0"))),
        currency=str(claim.get("currency", "USD")),
        loss_type=str(claim.get("lossType", "collision")),
        claimant_id=str(claim.get("claimantId", "unknown")),
        raw_vendor_id=str(claim.get("id", "")),
        fraud_signals=list(claim.get("fraudIndicators", [])),
    )


def from_snapsheet(payload: dict[str, Any]) -> NormalizedFnol:
    """Snapsheet claims API webhook shape (simplified)."""
    data = payload.get("data", payload)
    return NormalizedFnol(
        vendor="snapsheet",
        claim_id=str(data.get("claim_number") or data.get("id")),
        policy_number=str(data.get("policy_number", "POL-AUTO-001")),
        loss_date=_parse_date(str(data.get("date_of_loss", date.today().isoformat()))),
        reported_amount=Decimal(str(data.get("reserve_amount", data.get("amount", "0")))),
        currency=str(data.get("currency_code", "USD")),
        loss_type=str(data.get("loss_type", "unknown")),
        claimant_id=str(data.get("claimant_id", "unknown")),
        raw_vendor_id=str(data.get("id", "")),
        fraud_signals=list(data.get("flags", [])),
    )


def from_majesco(payload: dict[str, Any]) -> NormalizedFnol:
    """Majesco Claims+ event shape (simplified)."""
    event = payload.get("claimEvent", payload)
    return NormalizedFnol(
        vendor="majesco",
        claim_id=str(event.get("claimRef", event.get("claimId"))),
        policy_number=str(event.get("policyRef", "POL-PROP-001")),
        loss_date=_parse_date(str(event.get("incidentDate", date.today().isoformat()))),
        reported_amount=Decimal(str(event.get("estimatedLoss", "0"))),
        currency=str(event.get("currency", "USD")),
        loss_type=str(event.get("perilCode", "property")),
        claimant_id=str(event.get("insuredId", "unknown")),
        raw_vendor_id=str(event.get("eventId", "")),
        fraud_signals=list(event.get("siuFlags", [])),
    )


def from_acturis(payload: dict[str, Any]) -> NormalizedFnol:
    """Acturis (UK) claims notification webhook shape (simplified)."""
    note = payload.get("notification", payload.get("claimNotification", payload))
    return NormalizedFnol(
        vendor="acturis",
        claim_id=str(note.get("claimReference") or note.get("claimRef")),
        policy_number=str(note.get("policyReference", "POL-MOTOR-UK-001")),
        loss_date=_parse_date(str(note.get("dateOfLoss", note.get("lossDate", date.today().isoformat())))),
        reported_amount=Decimal(str(note.get("estimatedAmount", note.get("reserveAmount", "0")))),
        currency=str(note.get("currencyCode", "GBP")),
        loss_type=str(note.get("perilType", "motor")),
        claimant_id=str(note.get("policyholderId", "unknown")),
        raw_vendor_id=str(note.get("notificationId", "")),
        fraud_signals=list(note.get("fraudFlags", [])),
    )


def from_ice(payload: dict[str, Any]) -> NormalizedFnol:
    """ICE InsureTech (UK) Open Claims notification shape (simplified)."""
    note = payload.get("claimNotification", payload.get("notification", payload))
    return NormalizedFnol(
        vendor="ice",
        claim_id=str(note.get("claimReference") or note.get("claimNumber")),
        policy_number=str(note.get("policyNumber", note.get("policyReference", "POL-MOTOR-UK-001"))),
        loss_date=_parse_date(str(note.get("dateOfLoss", note.get("incidentDate", date.today().isoformat())))),
        reported_amount=Decimal(str(note.get("estimatedReserve", note.get("reserveAmount", "0")))),
        currency=str(note.get("currency", "GBP")),
        loss_type=str(note.get("perilCode", note.get("claimType", "motor"))),
        claimant_id=str(note.get("insuredId", note.get("policyholderId", "unknown"))),
        raw_vendor_id=str(note.get("notificationId", note.get("eventId", ""))),
        fraud_signals=list(note.get("fraudIndicators", note.get("referralFlags", []))),
    )


def from_ssp(payload: dict[str, Any]) -> NormalizedFnol:
    """SSP (UK) Open Claims / Pure cloud event shape (simplified)."""
    event = payload.get("claim", payload.get("event", payload))
    return NormalizedFnol(
        vendor="ssp",
        claim_id=str(event.get("claimNumber") or event.get("claimRef")),
        policy_number=str(event.get("policyNumber", "POL-MOTOR-UK-001")),
        loss_date=_parse_date(str(event.get("dateOfLoss", date.today().isoformat()))),
        reported_amount=Decimal(str(event.get("initialReserve", event.get("amount", "0")))),
        currency=str(event.get("currency", "GBP")),
        loss_type=str(event.get("claimType", "motor")),
        claimant_id=str(event.get("insuredPartyId", "unknown")),
        raw_vendor_id=str(event.get("eventId", "")),
        fraud_signals=list(event.get("referralFlags", [])),
    )


_ADAPTERS = {
    "guidewire": from_guidewire,
    "snapsheet": from_snapsheet,
    "majesco": from_majesco,
    "acturis": from_acturis,
    "ice": from_ice,
    "ssp": from_ssp,
}


def normalize_fnol(vendor: str, payload: dict[str, Any]) -> NormalizedFnol:
    adapter = _ADAPTERS.get(vendor.lower())
    if adapter is None:
        raise ValueError(f"unsupported FNOL vendor: {vendor}")
    return adapter(payload)
