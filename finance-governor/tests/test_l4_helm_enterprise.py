"""L4 Gold Helm enterprise manifest gate."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
CHART = ROOT / "deploy" / "helm" / "finance-governor"


def _render_enterprise() -> list[dict]:
    cmd = [
        "helm",
        "template",
        "fg",
        str(CHART),
        "-f",
        str(CHART / "values-production.yaml"),
        "-f",
        str(CHART / "values-enterprise.yaml"),
        "--set",
        "postgres.password=postgres",
        "--set",
        "secrets.create=true",
        "--set",
        "oidc.issuerUrl=https://idp.example.com",
        "--set",
        "oidc.audience=finance-governor",
        "--set",
        "s3Anchor.bucket=fg-anchor-l4",
    ]
    out = subprocess.check_output(cmd, text=True)
    docs = [d for d in yaml.safe_load_all(out) if d]
    return docs


@pytest.fixture(scope="module")
def enterprise_docs():
    return _render_enterprise()


def _kinds(docs: list[dict]) -> set[str]:
    return {d.get("kind") for d in docs if d.get("kind")}


def test_l4_pgbouncer_deployed(enterprise_docs):
    assert "Deployment" in _kinds(enterprise_docs)
    names = [d["metadata"]["name"] for d in enterprise_docs if d.get("metadata")]
    assert "fg-pgbouncer" in names


def test_l4_redis_sentinel_deployed(enterprise_docs):
    names = [d["metadata"]["name"] for d in enterprise_docs if d.get("metadata")]
    assert "fg-redis-sentinel" in names
    assert "fg-redis-master" in names


def test_l4_hpa_deployed(enterprise_docs):
    assert "HorizontalPodAutoscaler" in _kinds(enterprise_docs)


def test_l4_platforms_deployed(enterprise_docs):
    names = [d["metadata"]["name"] for d in enterprise_docs if d.get("metadata")]
    for plat in ("fg-wirematch", "fg-algofreeze", "fg-subledger", "fg-assetledger", "fg-creditgovern"):
        assert plat in names


def test_l4_podmonitor_and_prometheus_rules(enterprise_docs):
    kinds = _kinds(enterprise_docs)
    assert "PodMonitor" in kinds
    assert "PrometheusRule" in kinds


def test_l4_pdb_and_network_policy(enterprise_docs):
    kinds = _kinds(enterprise_docs)
    assert "PodDisruptionBudget" in kinds
    assert "NetworkPolicy" in kinds


def test_l4_platform_canary_cronjob(enterprise_docs):
    names = [d["metadata"]["name"] for d in enterprise_docs if d.get("kind") == "CronJob"]
    assert "fg-platform-canary" in names


def test_l4_no_simple_redis_when_sentinel(enterprise_docs):
    names = [d["metadata"]["name"] for d in enterprise_docs if d.get("metadata")]
    assert "fg-redis" not in names
