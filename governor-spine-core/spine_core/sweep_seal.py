"""K3 — reconciler sweep hash-seal conformance across all four governors."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from spine_core.config import GovernorDomain

REPO_ROOT = Path(__file__).resolve().parents[2]

SWEEP_EVENT_TYPES: dict[GovernorDomain, frozenset[str]] = {
    GovernorDomain.MODEL: frozenset({"EXPIRED_SWEEP", "STRANDED_HOLD"}),
    GovernorDomain.FINANCE: frozenset({"HORIZON_EXPIRED", "STRANDED_HOLD"}),
    GovernorDomain.INSURANCE: frozenset({"HORIZON_EXPIRED", "STRANDED_HOLD"}),
    GovernorDomain.CYBER: frozenset({"HORIZON_EXPIRED", "STRANDED_HOLD"}),
}


@dataclass(frozen=True)
class SweepAppendSpec:
    rel_path: str
    sealed_append_fn: str
    forbidden_raw_insert: str


SWEEP_APPEND_REGISTRY: dict[GovernorDomain, SweepAppendSpec] = {
    GovernorDomain.MODEL: SweepAppendSpec(
        rel_path="reconciler/app/sweeper.py",
        sealed_append_fn="append_sealed_ledger_event",
        forbidden_raw_insert="INSERT INTO ledger_events",
    ),
    GovernorDomain.FINANCE: SweepAppendSpec(
        rel_path="finance-governor/spine/reconciler/app/horizon_sweeper.py",
        sealed_append_fn="append_decision_event",
        forbidden_raw_insert="INSERT INTO decision_events",
    ),
    GovernorDomain.INSURANCE: SweepAppendSpec(
        rel_path="insurance-governor/spine/reconciler/app/horizon_sweeper.py",
        sealed_append_fn="append_claim_event",
        forbidden_raw_insert="INSERT INTO claim_events",
    ),
    GovernorDomain.CYBER: SweepAppendSpec(
        rel_path="cybersecurity-governor/spine/reconciler/app/horizon_sweeper.py",
        sealed_append_fn="append_security_event",
        forbidden_raw_insert="INSERT INTO security_events",
    ),
}


def _source_calls_fn(source: str, fn_name: str) -> bool:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == fn_name:
                return True
            if isinstance(func, ast.Attribute) and func.attr == fn_name:
                return True
    return False


def sweep_conformance_failures(repo_root: Path | None = None) -> list[str]:
    """Static K3 checks — sweepers must use sealed append helpers, not raw INSERT."""
    root = repo_root or REPO_ROOT
    failures: list[str] = []

    for domain, spec in SWEEP_APPEND_REGISTRY.items():
        path = root / spec.rel_path
        if not path.is_file():
            failures.append(f"{domain.value}: missing sweeper module {spec.rel_path}")
            continue

        source = path.read_text(encoding="utf-8")
        if not _source_calls_fn(source, spec.sealed_append_fn):
            failures.append(
                f"{domain.value}: {spec.rel_path} must call {spec.sealed_append_fn}() for sweep events"
            )
        if spec.forbidden_raw_insert in source:
            failures.append(
                f"{domain.value}: {spec.rel_path} must not raw-insert into ledger "
                f"({spec.forbidden_raw_insert}) — use {spec.sealed_append_fn}"
            )

    return failures
