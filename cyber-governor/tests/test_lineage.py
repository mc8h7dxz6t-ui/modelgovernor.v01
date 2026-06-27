"""Lineage normalization tests."""
from platforms.common.lineage import is_critical_edge, normalize_lineage


def test_normalize_falco_shell():
    edge = normalize_lineage(
        "falco",
        {
            "rule": "Terminal shell in container",
            "priority": "Critical",
            "time": "2026-06-26T12:00:00Z",
            "output_fields": {"proc.name": "bash", "proc.pname": "sh", "user.name": "root"},
        },
    )
    assert edge.source_system == "falco"
    assert edge.edge_type == "process_exec"
    assert edge.principal_id == "root"
    assert is_critical_edge(edge) is True


def test_normalize_tetragon_connect():
    edge = normalize_lineage(
        "tetragon",
        {
            "process_connect": {
                "process": {"exec_id": "e1", "binary": "/bin/curl", "pod": {"name": "payments"}},
                "socket": {"address": "203.0.113.50:443"},
            },
            "time": "2026-06-26T12:00:01Z",
        },
    )
    assert edge.edge_type == "socket_connect"
    assert edge.principal_id == "payments"
    assert edge.severity == "critical"
