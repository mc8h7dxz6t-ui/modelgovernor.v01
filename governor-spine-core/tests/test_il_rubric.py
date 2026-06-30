"""Tests for IL rubric evaluator."""
from __future__ import annotations

from pathlib import Path

from spine_core.il_rubric import ENGINEERING_CEILING, IL_TARGET, evaluate_governor, evaluate_portfolio
from spine_core.il_rubric import GOVERNOR_SPECS


def test_portfolio_rubric_has_four_governors():
    report = evaluate_portfolio(Path(__file__).resolve().parents[2])
    assert len(report["governors"]) == 4
    assert report["kernel_score"] == 9.0
    assert report["portfolio_engineering_score"] >= 7.0


def test_finance_hero_row_green_when_integration_tests_present():
    root = Path(__file__).resolve().parents[2]
    rubric = evaluate_governor(root, GOVERNOR_SPECS["FINANCE"])
    hero = next(r for r in rubric.rows if r.id == 4)
    assert hero.green is True


def test_phase_c_row_red_without_artifact():
    root = Path(__file__).resolve().parents[2]
    rubric = evaluate_governor(root, GOVERNOR_SPECS["MODEL"])
    phase_c = next(r for r in rubric.rows if r.id == 5)
    assert phase_c.green is False
    assert rubric.il_score < IL_TARGET
    assert rubric.engineering_score <= ENGINEERING_CEILING


def test_governor_dimension_scores_present():
    root = Path(__file__).resolve().parents[2]
    rubric = evaluate_governor(root, GOVERNOR_SPECS["CYBER"])
    dims = rubric.dimension_scores()
    assert set(dims) == {"architecture", "code", "execution", "robustness", "reliability"}
