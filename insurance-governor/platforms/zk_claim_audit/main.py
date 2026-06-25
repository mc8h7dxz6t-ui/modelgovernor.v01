"""ZkClaimAudit — cryptographic claim fact commitments for examiner-grade audit."""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from platforms.common.platform_sdk import GovernedPlatform, spine_health_payload
from platforms.common.persistence.commitment_store import get_commitment_store

from .proof_gate import AuditProofBundle, build_audit_proof, seal_claim_facts, verify_audit_proof

app = FastAPI(title="zkclaimaudit", version="0.1.0")
_GOVERNED = GovernedPlatform("zk_claim_audit")
_STORE = get_commitment_store()


class SealRequest(BaseModel):
    claim_id: str
    private_facts: dict[str, Any] = Field(default_factory=dict)
    account_id: str = "carrier-default"
    policy_id: str = "zk-audit-us"


class AuditRequest(BaseModel):
    claim_id: str
    disclosed_facts: dict[str, Any] = Field(default_factory=dict)


@app.get("/healthz")
def healthz() -> dict:
    return spine_health_payload("zk_claim_audit")


@app.get("/readyz")
def readyz() -> dict:
    return healthz()


@app.post("/audit/seal")
def seal(request: SealRequest) -> dict:
    commitment = seal_claim_facts(claim_id=request.claim_id, private_facts=request.private_facts)
    _STORE.save(request.claim_id, commitment, request.private_facts)
    facets = {
        "claim_id": request.claim_id,
        "commitment_hash": commitment.commitment_hash,
        "fact_count": commitment.fact_count,
        "audit_decision": "SEALED",
    }
    crystal_id = _GOVERNED.govern_operation(
        request.claim_id,
        facets,
        decision="SEALED",
        reserve_amount="0",
        account_id=request.account_id,
        policy_id=request.policy_id,
        outcome="sealed",
    )
    return {
        "commitment_id": commitment.commitment_id,
        "commitment_hash": commitment.commitment_hash,
        "crystal_id": crystal_id,
    }


@app.post("/audit/prove")
def prove(request: AuditRequest) -> dict:
    commitment = _STORE.get(request.claim_id)
    if commitment is None:
        raise HTTPException(status_code=404, detail="commitment not found")
    bundle = build_audit_proof(
        claim_id=request.claim_id,
        commitment=commitment,
        disclosed_facts=request.disclosed_facts,
    )
    if not bundle.valid:
        raise HTTPException(status_code=422, detail="disclosed facts do not match commitment")
    facets = {
        "claim_id": request.claim_id,
        "commitment_hash": bundle.commitment_hash,
        "proof_hash": bundle.proof_hash,
        "audit_decision": "VERIFIED",
    }
    crystal_id = _GOVERNED.govern_operation(
        f"{request.claim_id}-audit",
        facets,
        decision="VERIFIED",
        reserve_amount="0",
        outcome="verified",
    )
    return {"proof_hash": bundle.proof_hash, "valid": bundle.valid, "crystal_id": crystal_id}


@app.post("/audit/verify")
def verify(bundle: AuditProofBundle) -> dict:
    return {"valid": verify_audit_proof(bundle)}
