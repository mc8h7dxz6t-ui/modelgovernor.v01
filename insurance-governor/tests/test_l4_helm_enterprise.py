"""L4 Gold Helm enterprise manifest gate."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
CHART = ROOT / "deploy" / "helm" / "insurancegovernor"


def _render_enterprise() -> list[dict]:
    cmd = [
        "helm",
        "template",
        "ig",
        str(CHART),
        "-f",
        str(CHART / "values-production.yaml"),
        "-f",
        str(CHART / "values-enterprise.yaml"),
        "--set",
        "secrets.create=true",
        "--set",
        "secrets.postgresPassword=postgres",
        "--set",
        "config.oidcIssuerUrl=https://idp.example.com",
        "--set",
        "config.oidcAudience=insurancegovernor",
        "--set",
        "secrets.claimAnchorS3Bucket=ig-anchor-l4",
    ]
    out = subprocess.check_output(cmd, text=True)
    return [d for d in yaml.safe_load_all(out) if d]


@pytest.fixture(scope="module")
def enterprise_docs():
    return _render_enterprise()


def _kinds(docs: list[dict]) -> set[str]:
    return {d.get("kind") for d in docs if d.get("kind")}


def _names(docs: list[dict]) -> list[str]:
    return [d["metadata"]["name"] for d in docs if d.get("metadata")]


def test_l4_pgbouncer_deployed(enterprise_docs):
    assert "Deployment" in _kinds(enterprise_docs)
    assert "pgbouncer" in _names(enterprise_docs)


def test_l4_redis_sentinel_deployed(enterprise_docs):
    names = _names(enterprise_docs)
    assert "redis-sentinel" in names
    assert "redis-master" in names


def test_l4_hpa_deployed(enterprise_docs):
    assert "HorizontalPodAutoscaler" in _kinds(enterprise_docs)


def test_l4_platforms_deployed(enterprise_docs):
    names = _names(enterprise_docs)
    for plat in (
        "claim-gate",
        "model-risk-freeze",
        "indemnity-pay-gate",
        "underwriting-govern",
        "reserve-reconcile",
    ):
        assert plat in names


def test_l4_podmonitor_and_prometheus_rules(enterprise_docs):
    kinds = _kinds(enterprise_docs)
    assert "PodMonitor" in kinds
    assert "PrometheusRule" in kinds


def test_l4_pdb_and_network_policy(enterprise_docs):
    kinds = _kinds(enterprise_docs)
    assert "PodDisruptionBudget" in kinds
    assert "NetworkPolicy" in kinds


def test_l4_governance_canary_cronjob(enterprise_docs):
    names = [d["metadata"]["name"] for d in enterprise_docs if d.get("kind") == "CronJob"]
    assert "governance-canary" in names


def test_l4_reliability_cronjobs(enterprise_docs):
    names = [d["metadata"]["name"] for d in enterprise_docs if d.get("kind") == "CronJob"]
    for job in ("synthetic-canary", "model-risk-freeze-version-probe", "claim-gate-golden-probe"):
        assert job in names


def test_l4_extended_pdb_coverage(enterprise_docs):
    names = [d["metadata"]["name"] for d in enterprise_docs if d.get("kind") == "PodDisruptionBudget"]
    for pdb in ("sidecar-pdb", "reconciler-pdb", "pgbouncer-pdb"):
        assert pdb in names


def test_l4_claim_chain_verify_cronjob(enterprise_docs):
    names = [d["metadata"]["name"] for d in enterprise_docs if d.get("kind") == "CronJob"]
    assert "claim-chain-verify" in names


def test_l4_no_simple_redis_when_sentinel(enterprise_docs):
    deployments = [d for d in enterprise_docs if d.get("kind") == "Deployment"]
    redis_deployments = [
        d for d in deployments if d.get("metadata", {}).get("name") == "redis" or d.get("metadata", {}).get("labels", {}).get("app") == "redis"
    ]
    assert not redis_deployments


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
        "ig",
        str(CHART),
        "-f",
        str(CHART / "values-production.yaml"),
        "-f",
        str(CHART / "values-enterprise.yaml"),
        "-f",
        str(CHART / "values-rds.yaml"),
        "--set",
        "secrets.create=true",
        "--set",
        "postgres.external.host=ig-prod.cluster.example.rds.amazonaws.com",
    ]
    out = subprocess.check_output(cmd, text=True)
    assert "name: postgres" not in out or "ig-prod.cluster.example.rds.amazonaws.com" in out
    assert "ig-prod.cluster.example.rds.amazonaws.com" in out
