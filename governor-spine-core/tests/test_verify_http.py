"""HTTP verify-chain helper tests."""

from spine_core.config import GovernorDomain
from spine_core.verify_http import VerifyResult, verify_domain_chain_http


def test_verify_http_unreachable_returns_none_valid(monkeypatch):
    def _boom(*_a, **_k):
        raise OSError("connection refused")

    monkeypatch.setattr("urllib.request.urlopen", _boom)
    result = verify_domain_chain_http(GovernorDomain.CYBER)
    assert result.valid is None
    assert "8121" in result.url


def test_verify_http_parses_valid_response(monkeypatch):
    class _Resp:
        def read(self):
            return b'{"valid": true, "events": 3}'

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **k: _Resp())
    result = verify_domain_chain_http(GovernorDomain.CYBER)
    assert result.valid is True
    assert result.raw["events"] == 3
