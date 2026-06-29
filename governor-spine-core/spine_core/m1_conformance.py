"""M1 spine consolidation conformance — shared checkpoint, mesh, metadata, routes."""

from __future__ import annotations

import ast
from pathlib import Path

from spine_core.commit_registry import COMMIT_MODULE_REGISTRY, MODEL_COMMIT_MODULE
from spine_core.config import GovernorDomain
from spine_core.verify_route_registry import VERIFY_ROUTE_REGISTRY, verify_route_path

REPO_ROOT = Path(__file__).resolve().parents[2]

CHAIN_CHECKPOINT_SHIMS = [
    "sidecar/app/chain_checkpoint.py",
    "finance-governor/spine/sidecar/app/chain_checkpoint.py",
    "insurance-governor/spine/sidecar/app/chain_checkpoint.py",
    "cybersecurity-governor/spine/sidecar/app/chain_checkpoint.py",
]

SEAL_MODULES = [
    "sidecar/app/ledger_seal.py",
    "finance-governor/spine/sidecar/app/decision_seal.py",
    "insurance-governor/spine/sidecar/app/claim_seal.py",
    "cybersecurity-governor/spine/sidecar/app/security_seal.py",
]


def defined_functions(module_path: Path) -> set[str]:
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    return {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}


def m1_conformance_failures(repo_root: Path | None = None) -> list[str]:
    root = repo_root or REPO_ROOT
    failures: list[str] = []

    for rel_path in CHAIN_CHECKPOINT_SHIMS:
        path = root / rel_path
        if not path.is_file():
            failures.append(f"M1: missing chain_checkpoint shim {rel_path}")
            continue
        source = path.read_text(encoding="utf-8")
        if "spine_core.chain_checkpoint" not in source:
            failures.append(f"M1: {rel_path} must re-export spine_core.chain_checkpoint")

    for rel_path in SEAL_MODULES:
        path = root / rel_path
        if not path.is_file():
            failures.append(f"M1: missing seal module {rel_path}")
            continue
        source = path.read_text(encoding="utf-8")
        if "spine_core.metadata" not in source:
            failures.append(f"M1: {rel_path} must import normalize_metadata from spine_core.metadata")

    for domain, spec in COMMIT_MODULE_REGISTRY.items():
        path = root / spec.rel_path
        if not path.is_file():
            failures.append(f"{domain.value}: missing commit module {spec.rel_path}")
            continue
        source = path.read_text(encoding="utf-8")
        fns = defined_functions(path)
        if spec.crystallize_fn not in fns:
            failures.append(f"{domain.value}: missing {spec.crystallize_fn}() in {spec.rel_path}")
        if spec.commit_fn not in fns:
            failures.append(f"{domain.value}: missing {spec.commit_fn}() in {spec.rel_path}")
        if "spine_core.commit_mesh" not in source:
            failures.append(f"{domain.value}: {spec.rel_path} must use spine_core.commit_mesh")
        if "spine_core.commit_helpers" not in source:
            failures.append(f"{domain.value}: {spec.rel_path} must use spine_core.commit_helpers")

    mg_ledger = root / MODEL_COMMIT_MODULE
    if not mg_ledger.is_file():
        failures.append("MODEL_GOVERNOR: missing sidecar/app/ledger.py")

    for domain, spec in VERIFY_ROUTE_REGISTRY.items():
        path = root / spec.rel_path
        if not path.is_file():
            failures.append(f"{domain.value}: missing routes module {spec.rel_path}")
            continue
        source = path.read_text(encoding="utf-8")
        route_suffix = verify_route_path(domain)
        if route_suffix not in source:
            failures.append(f"{domain.value}: {spec.rel_path} missing route /{route_suffix}")
        if spec.verify_fn not in source:
            failures.append(f"{domain.value}: {spec.rel_path} must call {spec.verify_fn}()")

    return failures
