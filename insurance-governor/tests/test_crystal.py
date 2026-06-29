from platforms.common.crystal import seal_crystal, verify_commit_fingerprint


def test_crystal_fingerprint_roundtrip():
    facets = {"amount": "100.00"}
    crystal = seal_crystal(platform="claim_gate", operation_id="op1", risk_tier="high", facets=facets)
    assert verify_commit_fingerprint(crystal, facets) is True
    assert verify_commit_fingerprint(crystal, {"amount": "200.00"}) is False
