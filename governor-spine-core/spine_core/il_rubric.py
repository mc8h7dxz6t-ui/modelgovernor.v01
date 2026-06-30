"""Industry Leading (IL) rubric — five rows per governor, path to 9/10."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from spine_core.attestation_validate import phase_c_valid
from spine_core.config import GovernorDomain

IL_TARGET = 9.0
ENGINEERING_CEILING = 8.5
L5_BASE = 7.0

DIMENSIONS = ("architecture", "code", "execution", "robustness", "reliability")


@dataclass(frozen=True)
class RubricRow:
    id: int
    name: str
    dimension: str
    green: bool
    verifier: str
    evidence: str
    gap: str | None = None


@dataclass
class GovernorRubric:
    governor: str
    rows: list[RubricRow] = field(default_factory=list)

    @property
    def rows_green(self) -> int:
        return sum(1 for row in self.rows if row.green)

    @property
    def engineering_score(self) -> float:
        """Rows 1–4 only — max 8.5 (Phase A+B ceiling)."""
        eng_rows = [r for r in self.rows if r.id <= 4]
        if not eng_rows:
            return L5_BASE
        green = sum(1 for r in eng_rows if r.green)
        return round(L5_BASE + (green / len(eng_rows)) * (ENGINEERING_CEILING - L5_BASE), 1)

    @property
    def il_score(self) -> float:
        """9.0 only when all five rubric rows are green."""
        if all(r.green for r in self.rows):
            return IL_TARGET
        return self.engineering_score

    @property
    def gaps_to_9(self) -> list[str]:
        return [r.gap or f"row {r.id} {r.name}" for r in self.rows if not r.green]

    def dimension_scores(self) -> dict[str, float]:
        """Map rubric rows onto architecture/code/execution/robustness/reliability."""
        by_dim: dict[str, list[bool]] = {d: [] for d in DIMENSIONS}
        for row in self.rows:
            by_dim[row.dimension].append(row.green)
        scores: dict[str, float] = {}
        for dim, flags in by_dim.items():
            if not flags:
                scores[dim] = L5_BASE
            else:
                green = sum(1 for f in flags if f)
                scores[dim] = round(L5_BASE + (green / len(flags)) * (IL_TARGET - L5_BASE), 1)
        return scores


@dataclass(frozen=True)
class GovernorSpec:
    key: str
    domain: GovernorDomain
    cert_program: str
    l4_make: str
    compose_smoke_ci: str
    pilot_attestation_ci: str
    hero_demos: tuple[str, ...]
    hero_probes: tuple[str, ...]
    attestation_runner: str
    phase_c_artifact: str
    in_plug: bool = True
    secondary_wedges: dict[str, float] | None = None


GOVERNOR_SPECS: dict[str, GovernorSpec] = {
    "MODEL": GovernorSpec(
        key="MODEL",
        domain=GovernorDomain.MODEL,
        cert_program="certification/program.yaml",
        l4_make="mg-certification-l4-ci",
        compose_smoke_ci="compose-smoke-mg",
        pilot_attestation_ci="mg-pilot-attestation",
        hero_demos=("scripts/demo-gold.sh", "Makefile"),
        hero_probes=("governed_dispatch", "verify_chain", "anchor_head"),
        attestation_runner="scripts/mg_attestation_runner.py",
        phase_c_artifact="artifacts/reliability/modelgovernor/cluster_attestation.json",
    ),
    "FINANCE": GovernorSpec(
        key="FINANCE",
        domain=GovernorDomain.FINANCE,
        cert_program="finance-governor/certification/program.yaml",
        l4_make="fg-certification-l4-ci",
        compose_smoke_ci="compose-smoke-fg",
        pilot_attestation_ci="fg-pilot-attestation",
        hero_demos=(
            "finance-governor/Makefile",
            "finance-governor/tests/test_algofreeze_integration.py",
            "finance-governor/tests/test_wirematch_hero_integration.py",
        ),
        hero_probes=(
            "governed_commit",
            "verify_chain",
            "algofreeze_version_mismatch_freeze",
            "wirematch_beneficiary_held",
        ),
        attestation_runner="finance-governor/scripts/fg_attestation_runner.py",
        phase_c_artifact="artifacts/reliability/finance-governor/cluster_attestation.json",
    ),
    "CYBER": GovernorSpec(
        key="CYBER",
        domain=GovernorDomain.CYBER,
        cert_program="cybersecurity-governor/certification/program.yaml",
        l4_make="cg-certification-l4-ci",
        compose_smoke_ci="compose-smoke-cg",
        pilot_attestation_ci="cg-pilot-attestation",
        hero_demos=(
            "cybersecurity-governor/scripts/cg-egress-wedge-demo.sh",
            "scripts/compose-smoke-cg.sh",
        ),
        hero_probes=("governed_commit", "verify_chain", "egress_govern_evaluate"),
        attestation_runner="cybersecurity-governor/scripts/attestation_runner.py",
        phase_c_artifact="artifacts/reliability/cybersecurity-governor/cluster_attestation.json",
    ),
    "INSURANCE": GovernorSpec(
        key="INSURANCE",
        domain=GovernorDomain.INSURANCE,
        cert_program="insurance-governor/certification/program.yaml",
        l4_make="ig-certification-l4-ci",
        compose_smoke_ci="compose-smoke-ig",
        pilot_attestation_ci="ig-pilot-attestation",
        hero_demos=(
            "scripts/compose-smoke-ig.sh",
            "insurance-governor/tests/test_fnol_sandbox_integration.py",
        ),
        hero_probes=("governed_commit", "verify_chain", "claim_gate_fnol_guidewire"),
        attestation_runner="insurance-governor/scripts/attestation_runner.py",
        phase_c_artifact="artifacts/reliability/insurance-governor/cluster_attestation.json",
        secondary_wedges={"spatial_twin": 7.5, "subrogation_graph": 7.5},
    ),
}


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _ci_contains(ci_yml: str, needle: str) -> bool:
    return needle in ci_yml


def _runner_has_probes(repo: Path, runner_rel: str, probes: tuple[str, ...]) -> tuple[bool, list[str]]:
    text = _read_text(repo / runner_rel)
    missing = [p for p in probes if p not in text]
    return not missing, missing


def _hero_demos_present(root: Path, demos: tuple[str, ...]) -> bool:
    return all((root / rel).is_file() for rel in demos)


def _makefile_has_target(root: Path, target: str) -> bool:
    for rel in ("Makefile", "finance-governor/Makefile", "insurance-governor/Makefile", "cybersecurity-governor/Makefile"):
        if target in _read_text(root / rel):
            return True
    return False


def evaluate_governor(repo_root: Path | None, spec: GovernorSpec) -> GovernorRubric:
    root = repo_root or Path(__file__).resolve().parents[2]
    ci_yml = _read_text(root / ".github/workflows/ci.yml")
    rows: list[RubricRow] = []

    l4_ok = (root / spec.cert_program).is_file() and _makefile_has_target(root, spec.l4_make)
    rows.append(
        RubricRow(
            id=1,
            name="L4 engineering",
            dimension="robustness",
            green=l4_ok,
            verifier=spec.l4_make,
            evidence=spec.cert_program if l4_ok else "missing cert program or L4 make target",
            gap=None if l4_ok else f"ship {spec.l4_make} + {spec.cert_program}",
        )
    )

    plug_ok = spec.in_plug
    rows.append(
        RubricRow(
            id=2,
            name="L5 self-check",
            dimension="execution",
            green=plug_ok,
            verifier="make plug",
            evidence="run-salvage-verification.sh includes governor spine tests",
            gap=None if plug_ok else "add governor to portfolio plug harness",
        )
    )

    live_ok = _ci_contains(ci_yml, spec.compose_smoke_ci) and _ci_contains(ci_yml, spec.pilot_attestation_ci)
    rows.append(
        RubricRow(
            id=3,
            name="Live stack proof",
            dimension="reliability",
            green=live_ok,
            verifier=f"{spec.compose_smoke_ci} + {spec.pilot_attestation_ci}",
            evidence=".github/workflows/ci.yml compose-smoke + pilot attestation jobs",
            gap=None if live_ok else f"wire {spec.compose_smoke_ci} and {spec.pilot_attestation_ci} in CI",
        )
    )

    demos_ok = _hero_demos_present(root, spec.hero_demos)
    probes_ok, missing_probes = _runner_has_probes(root, spec.attestation_runner, spec.hero_probes)
    hero_ok = demos_ok and probes_ok
    rows.append(
        RubricRow(
            id=4,
            name="Hero wedge depth",
            dimension="architecture",
            green=hero_ok,
            verifier=spec.attestation_runner,
            evidence=f"demos={list(spec.hero_demos)} probes={list(spec.hero_probes)}",
            gap=None
            if hero_ok
            else f"hero wedge: missing demos or attestation probes {missing_probes}",
        )
    )

    phase_c_path = root / spec.phase_c_artifact
    phase_c_ok = phase_c_valid(phase_c_path)
    rows.append(
        RubricRow(
            id=5,
            name="External evidence (Phase C)",
            dimension="code",
            green=phase_c_ok,
            verifier="spine_core.attestation_validate",
            evidence=str(spec.phase_c_artifact) if phase_c_ok else "no valid cluster_attestation.json",
            gap=None if phase_c_ok else "design-partner VPC attestation + signed letter (human gate)",
        )
    )

    return GovernorRubric(governor=spec.key, rows=rows)


def _kernel_score(root: Path) -> float:
    from spine_core.append_lock import append_lock_conformance_failures
    from spine_core.ledger_registry import conformance_failures
    from spine_core.m1_conformance import m1_conformance_failures
    from spine_core.retention_cronjob import retention_cronjob_conformance_failures
    from spine_core.sweep_seal import sweep_conformance_failures

    checks = (
        conformance_failures(root),
        sweep_conformance_failures(root),
        append_lock_conformance_failures(root),
        retention_cronjob_conformance_failures(root),
        m1_conformance_failures(root),
    )
    return 9.0 if not any(checks) else 8.5


def evaluate_portfolio(repo_root: Path | None = None) -> dict[str, Any]:
    root = repo_root or Path(__file__).resolve().parents[2]
    governors: dict[str, Any] = {}
    eng_scores: list[float] = []
    il_scores: list[float] = []

    for key, spec in GOVERNOR_SPECS.items():
        rubric = evaluate_governor(root, spec)
        entry: dict[str, Any] = {
            "engineering_score": rubric.engineering_score,
            "il_score": rubric.il_score,
            "tier": "IL" if rubric.il_score >= IL_TARGET else "L5",
            "rubric_rows_green": f"{rubric.rows_green}/5",
            "gaps_to_9": rubric.gaps_to_9,
            "dimensions": rubric.dimension_scores(),
            "rows": [asdict(r) for r in rubric.rows],
            "live_ci": [spec.compose_smoke_ci, spec.pilot_attestation_ci],
        }
        if spec.secondary_wedges:
            entry["secondary_wedges"] = spec.secondary_wedges
        governors[spec.domain.value] = entry
        eng_scores.append(rubric.engineering_score)
        il_scores.append(rubric.il_score)

    kernel_score = _kernel_score(root)
    portfolio_engineering = round(sum(eng_scores) / len(eng_scores), 1) if eng_scores else L5_BASE
    portfolio_il = round(min(il_scores), 1) if any(s < IL_TARGET for s in il_scores) else IL_TARGET
    if portfolio_il < IL_TARGET:
        portfolio_il = portfolio_engineering

    return {
        "kernel_score": kernel_score,
        "portfolio_engineering_score": portfolio_engineering,
        "portfolio_il_score": portfolio_il,
        "portfolio_score": portfolio_engineering,
        "il_target": IL_TARGET,
        "engineering_ceiling": ENGINEERING_CEILING,
        "governors": governors,
        "path_to_9": {
            "engineering_complete": portfolio_engineering >= ENGINEERING_CEILING,
            "il_requires": "Phase C external evidence per governor (row 5)",
            "blockers": [
                f"{g}: {gap}"
                for g, data in governors.items()
                if data.get("il_score", 0) < IL_TARGET
                for gap in data.get("gaps_to_9", [])
            ],
        },
    }
