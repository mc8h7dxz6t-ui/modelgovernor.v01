"""K1 ledger seal registry — maps each governor to its seal module implementation."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from spine_core.config import DOMAIN_REGISTRY, GovernorDomain

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class SealModuleSpec:
    rel_path: str
    verify_fn: str
    hash_fn: str = "compute_row_hash"
    seal_fn: str | None = None


SEAL_REGISTRY: dict[GovernorDomain, SealModuleSpec] = {
    GovernorDomain.MODEL: SealModuleSpec(
        rel_path="sidecar/app/ledger_seal.py",
        verify_fn="verify_ledger_chain",
        seal_fn="seal_ledger_event",
    ),
    GovernorDomain.FINANCE: SealModuleSpec(
        rel_path="finance-governor/spine/sidecar/app/decision_seal.py",
        verify_fn="verify_decision_chain",
        seal_fn="seal_decision_event",
    ),
    GovernorDomain.INSURANCE: SealModuleSpec(
        rel_path="insurance-governor/spine/sidecar/app/claim_seal.py",
        verify_fn="verify_claim_chain",
        seal_fn="seal_claim_event",
    ),
    GovernorDomain.CYBER: SealModuleSpec(
        rel_path="cybersecurity-governor/spine/sidecar/app/security_seal.py",
        verify_fn="verify_security_chain",
        seal_fn="seal_security_event",
    ),
}


def defined_functions(module_path: Path) -> set[str]:
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    return {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}


def conformance_failures(repo_root: Path | None = None) -> list[str]:
    root = repo_root or REPO_ROOT
    failures: list[str] = []

    for domain, spec in SEAL_REGISTRY.items():
        path = root / spec.rel_path
        if not path.is_file():
            failures.append(f"{domain.value}: missing seal module {spec.rel_path}")
            continue

        fns = defined_functions(path)
        registry = DOMAIN_REGISTRY[domain]

        if spec.verify_fn not in fns:
            failures.append(f"{domain.value}: missing {spec.verify_fn}() in {spec.rel_path}")
        if spec.hash_fn not in fns:
            failures.append(f"{domain.value}: missing {spec.hash_fn}() in {spec.rel_path}")
        if spec.seal_fn and spec.seal_fn not in fns:
            failures.append(f"{domain.value}: missing {spec.seal_fn}() in {spec.rel_path}")

        if registry.ledger_table not in path.read_text(encoding="utf-8"):
            failures.append(
                f"{domain.value}: {spec.rel_path} does not reference ledger table {registry.ledger_table}"
            )

    return failures
