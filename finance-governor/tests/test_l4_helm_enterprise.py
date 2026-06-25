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


def test_l4_reliability_cronjobs(enterprise_docs):
    names = [d["metadata"]["name"] for d in enterprise_docs if d.get("kind") == "CronJob"]
    for job in ("fg-synthetic-canary", "fg-algofreeze-version-probe", "fg-wirematch-golden-probe"):
        assert job in names


def test_l4_extended_pdb_coverage(enterprise_docs):
    names = [d["metadata"]["name"] for d in enterprise_docs if d.get("kind") == "PodDisruptionBudget"]
    for pdb in ("fg-reconciler-pdb", "fg-pgbouncer-pdb", "fg-platforms-pdb"):
        assert pdb in names


def test_l4_no_simple_redis_when_sentinel(enterprise_docs):
    names = [d["metadata"]["name"] for d in enterprise_docs if d.get("metadata")]
    assert "fg-redis" not in names


def test_l5_istio_injection_on_workloads(enterprise_docs):
    deployments = [d for d in enterprise_docs if d.get("kind") == "Deployment"]
    injected = [
        d
        for d in deployments
        if d.get("spec", {}).get("template", {}).get("metadata", {}).get("annotations", {}).get("sidecar.istio.io/inject") == "true"
    ]
    assert len(injected) >= 5


def test_l5_rds_overlay_no_in_cluster_postgres():
    cmd = [
        "helm",
        "template",
        "fg",
        str(CHART),
        "-f",
        str(CHART / "values-production.yaml"),
        "-f",
        str(CHART / "values-enterprise.yaml"),
        "-f",
        str(CHART / "values-rds.yaml"),
        "--set",
        "postgres.password=postgres",
        "--set",
        "secrets.create=true",
        "--set",
        "postgres.external.host=fg-prod.cluster.example.rds.amazonaws.com",
    ]
    out = subprocess.check_output(cmd, text=True)
    assert "fg-postgres" not in out
    assert "fg-prod.cluster.example.rds.amazonaws.com" in out
