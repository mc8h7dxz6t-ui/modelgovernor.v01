"""K1 ledger seal conformance across all four governors."""

from pathlib import Path

from spine_core.ledger_registry import SEAL_REGISTRY, conformance_failures, defined_functions


def test_all_four_governors_registered_in_seal_registry():
    assert len(SEAL_REGISTRY) == 4


def test_k1_conformance_no_failures():
    repo_root = Path(__file__).resolve().parents[2]
    failures = conformance_failures(repo_root)
    assert failures == [], "K1 ledger conformance gaps:\n" + "\n".join(failures)


def test_each_seal_module_has_verify_and_hash_functions():
    repo_root = Path(__file__).resolve().parents[2]
    for domain, spec in SEAL_REGISTRY.items():
        path = repo_root / spec.rel_path
        fns = defined_functions(path)
        assert spec.verify_fn in fns, f"{domain.value}: missing {spec.verify_fn}"
        assert spec.hash_fn in fns, f"{domain.value}: missing {spec.hash_fn}"
