from platforms.common.crystal import seal_crystal, verify_commit_fingerprint
from support.cyber_fixtures import EGRESS_PLATFORM, egress_facets


def test_crystal_fingerprint_roundtrip():
    facets = egress_facets(flow_id="op1")
    crystal = seal_crystal(platform=EGRESS_PLATFORM, operation_id="op1", risk_tier="high", facets=facets)
    assert verify_commit_fingerprint(crystal, facets) is True
    assert verify_commit_fingerprint(crystal, egress_facets(flow_id="op1", host="evil.example.com")) is False
