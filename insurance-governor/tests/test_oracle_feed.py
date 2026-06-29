from decimal import Decimal

from platforms.parametric_oracle.oracle_feed import attestation_hash, fetch_oracle_feed


def test_mock_usgs_feed():
    reading = fetch_oracle_feed(source="usgs-feed")
    assert reading.source == "usgs-feed"
    assert reading.metric_value == Decimal("7.2")
    assert reading.threshold == Decimal("6.5")
    assert reading.attestation_hash == attestation_hash(source=reading.source, payload=reading.payload)


def test_attestation_hash_deterministic():
    h1 = attestation_hash(source="chainlink", payload='{"value":1}')
    h2 = attestation_hash(source="chainlink", payload='{"value":1}')
    assert h1 == h2
