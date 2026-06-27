from platforms.zk_claim_audit.proof_gate import (
    build_audit_proof,
    seal_claim_facts,
    verify_audit_proof,
)


def test_seal_and_prove_claim_facts():
    private = {"loss_amount": "10000", "injury_severity": "minor"}
    commitment = seal_claim_facts(claim_id="zk-1", private_facts=private)
    bundle = build_audit_proof(
        claim_id="zk-1",
        commitment=commitment,
        disclosed_facts=private,
    )
    assert bundle.valid is True
    assert verify_audit_proof(bundle) is True


def test_mismatched_disclosure_fails():
    commitment = seal_claim_facts(claim_id="zk-2", private_facts={"a": "1"})
    bundle = build_audit_proof(
        claim_id="zk-2",
        commitment=commitment,
        disclosed_facts={"a": "2"},
    )
    assert bundle.valid is False


def test_zk_standalone_spine_adapter():
    from platforms.common.spine_adapter import CommitOutcome, SpineAdapter

    adapter = SpineAdapter(platform="zk_claim_audit", spine_enabled=False)
    facets = {"claim_id": "zk-local-1", "commitment_hash": "abc123"}
    crystal = adapter.crystallize("zk-local-1", "critical", facets)
    adapter.commit(
        CommitOutcome(
            operation_id="zk-local-1",
            crystal_id=crystal.crystal_id,
            facets=facets,
            outcome="sealed",
            committed_reserve="0",
        )
    )
