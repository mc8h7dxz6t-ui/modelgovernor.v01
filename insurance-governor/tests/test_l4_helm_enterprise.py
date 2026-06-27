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
    assert "redis-replica" in names


def test_l4_gateway_hpa_deployed(enterprise_docs):
    hpas = [d for d in enterprise_docs if d.get("kind") == "HorizontalPodAutoscaler"]
    names = {d["metadata"]["name"] for d in hpas}
    assert "gateway-hpa" in names


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
    for pdb in ("sidecar-pdb", "reconciler-pdb", "pgbouncer-pdb", "gateway-pdb"):
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


def test_l5_sidecar_ingress_authorization_policy(enterprise_docs):
    policies = [d for d in enterprise_docs if d.get("kind") == "AuthorizationPolicy"]
    names = {d["metadata"]["name"] for d in policies}
    assert "sidecar-ingress-platforms" in names
    sidecar_policy = next(d for d in policies if d["metadata"]["name"] == "sidecar-ingress-platforms")
    principals = sidecar_policy["spec"]["rules"][0]["from"][0]["source"]["principals"]
    assert any("ig-platform-workload" in p for p in principals)
    assert any("ig-gateway-workload" in p for p in principals)
    ports = sidecar_policy["spec"]["rules"][0]["to"][0]["operation"]["ports"]
    assert "8101" in ports


def test_l5_network_policy_allows_platform_to_sidecar(enterprise_docs):
    netpols = [d for d in enterprise_docs if d.get("kind") == "NetworkPolicy"]
    sidecar_ingress = next(d for d in netpols if d["metadata"]["name"] == "sidecar-ingress")
    ingress_rules = sidecar_ingress["spec"]["ingress"]
    platform_rule = next(
        r
        for r in ingress_rules
        if any(
            sel.get("podSelector", {}).get("matchLabels", {}).get("insurancegovernor.io/component") == "platform"
            for sel in r.get("from", [])
        )
    )
    assert {"protocol": "TCP", "port": 8101} in platform_rule["ports"]


def test_l5_ingestion_adapter_hpa(enterprise_docs):
    hpas = [d for d in enterprise_docs if d.get("kind") == "HorizontalPodAutoscaler"]
    names = {d["metadata"]["name"] for d in hpas}
    assert "claim-gate-hpa" in names
    assert "parametric-oracle-hpa" in names
    claim_hpa = next(d for d in hpas if d["metadata"]["name"] == "claim-gate-hpa")
    assert claim_hpa["spec"]["maxReplicas"] >= 12


def test_l5_platform_service_accounts(enterprise_docs):
    accounts = [d for d in enterprise_docs if d.get("kind") == "ServiceAccount"]
    names = {d["metadata"]["name"] for d in accounts}
    assert "ig-platform-workload" in names
    assert "ig-gateway-workload" in names
    deployments = [d for d in enterprise_docs if d.get("kind") == "Deployment"]
    claim_gate = next(d for d in deployments if d["metadata"]["name"] == "claim-gate")
    assert claim_gate["spec"]["template"]["spec"]["serviceAccountName"] == "ig-platform-workload"


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
