"""ZK-style claim fact commitments — tamper-evident selective disclosure for examiner audit."""
from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ClaimCommitment:
    commitment_id: str
    claim_id: str
    commitment_hash: str
    salt: str
    fact_count: int


@dataclass(frozen=True)
class AuditProofBundle:
    claim_id: str
    commitment_hash: str
    disclosed_facts: dict[str, Any]
    salt: str
    proof_hash: str
    valid: bool


def _canonical_facts(facts: dict[str, Any]) -> str:
    return json.dumps(facts, sort_keys=True, separators=(",", ":"))


def seal_claim_facts(*, claim_id: str, private_facts: dict[str, Any]) -> ClaimCommitment:
    salt = secrets.token_hex(16)
    payload = _canonical_facts({"claim_id": claim_id, "facts": private_facts, "salt": salt})
    commitment_hash = hashlib.sha256(payload.encode()).hexdigest()
    return ClaimCommitment(
        commitment_id=f"cc_{commitment_hash[:16]}",
        claim_id=claim_id,
        commitment_hash=commitment_hash,
        salt=salt,
        fact_count=len(private_facts),
    )


def build_audit_proof(
    *,
    claim_id: str,
    commitment: ClaimCommitment,
    disclosed_facts: dict[str, Any],
) -> AuditProofBundle:
    payload = _canonical_facts(
        {"claim_id": claim_id, "facts": disclosed_facts, "salt": commitment.salt}
    )
    recomputed = hashlib.sha256(payload.encode()).hexdigest()
    valid = recomputed == commitment.commitment_hash
    proof_hash = hashlib.sha256(
        f"{commitment.commitment_hash}:{_canonical_facts(disclosed_facts)}".encode()
    ).hexdigest()
    return AuditProofBundle(
        claim_id=claim_id,
        commitment_hash=commitment.commitment_hash,
        disclosed_facts=disclosed_facts,
        salt=commitment.salt,
        proof_hash=proof_hash,
        valid=valid,
    )


def verify_audit_proof(bundle: AuditProofBundle) -> bool:
    payload = _canonical_facts(
        {"claim_id": bundle.claim_id, "facts": bundle.disclosed_facts, "salt": bundle.salt}
    )
    return hashlib.sha256(payload.encode()).hexdigest() == bundle.commitment_hash
