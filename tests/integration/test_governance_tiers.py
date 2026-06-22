"""
Integration tests — governance tier classification and GET /admin/models coverage.
"""
from __future__ import annotations

from contextlib import contextmanager
from decimal import Decimal
import os
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SIDECAR_PATH = ROOT / "sidecar"
for p in (str(ROOT), str(SIDECAR_PATH)):
    if p not in sys.path:
        sys.path.insert(0, p)

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://localhost:5432/modelgovernor_test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SIDECAR_INTERNAL_TOKENS", "test-token")

from app.config import get_settings
from app.routes_reconcile import list_model_policy


VALID_TIERS = {"BUDGET", "STANDARD", "FRONTIER"}

# Representative fixture data covering all three tiers and multiple providers.
FIXTURE_MODELS: list[dict[str, Any]] = [
    # FRONTIER
    {
        "model_name": "o3",
        "provider": "openai",
        "governance_tier": "FRONTIER",
        "enabled": True,
        "max_input_tokens": 32000,
        "max_output_tokens": 4096,
        "max_cost_per_request": Decimal("75.000000"),
        "max_cost_per_trace": Decimal("150.000000"),
        "stream_allowed": False,
        "fallback_price_per_token": Decimal("0.002000"),
    },
    {
        "model_name": "claude-opus-4",
        "provider": "anthropic",
        "governance_tier": "FRONTIER",
        "enabled": True,
        "max_input_tokens": 200000,
        "max_output_tokens": 4096,
        "max_cost_per_request": Decimal("75.000000"),
        "max_cost_per_trace": Decimal("150.000000"),
        "stream_allowed": True,
        "fallback_price_per_token": Decimal("0.001800"),
    },
    # STANDARD
    {
        "model_name": "gpt-4o",
        "provider": "openai",
        "governance_tier": "STANDARD",
        "enabled": True,
        "max_input_tokens": 128000,
        "max_output_tokens": 4096,
        "max_cost_per_request": Decimal("20.000000"),
        "max_cost_per_trace": Decimal("50.000000"),
        "stream_allowed": True,
        "fallback_price_per_token": Decimal("0.000500"),
    },
    {
        "model_name": "gemini-2.5-pro",
        "provider": "google",
        "governance_tier": "STANDARD",
        "enabled": True,
        "max_input_tokens": 128000,
        "max_output_tokens": 8192,
        "max_cost_per_request": Decimal("20.000000"),
        "max_cost_per_trace": Decimal("50.000000"),
        "stream_allowed": True,
        "fallback_price_per_token": Decimal("0.000450"),
    },
    # BUDGET
    {
        "model_name": "gpt-4o-mini",
        "provider": "openai",
        "governance_tier": "BUDGET",
        "enabled": True,
        "max_input_tokens": 128000,
        "max_output_tokens": 4096,
        "max_cost_per_request": Decimal("5.000000"),
        "max_cost_per_trace": Decimal("25.000000"),
        "stream_allowed": True,
        "fallback_price_per_token": Decimal("0.000050"),
    },
    {
        "model_name": "deepseek-chat",
        "provider": "deepseek",
        "governance_tier": "BUDGET",
        "enabled": True,
        "max_input_tokens": 128000,
        "max_output_tokens": 4096,
        "max_cost_per_request": Decimal("5.000000"),
        "max_cost_per_trace": Decimal("25.000000"),
        "stream_allowed": True,
        "fallback_price_per_token": Decimal("0.000070"),
    },
    # Disabled model — must appear in total_count but not enabled_count
    {
        "model_name": "legacy-model",
        "provider": "openai",
        "governance_tier": "BUDGET",
        "enabled": False,
        "max_input_tokens": 4096,
        "max_output_tokens": 1024,
        "max_cost_per_request": Decimal("2.000000"),
        "max_cost_per_trace": Decimal("10.000000"),
        "stream_allowed": False,
        "fallback_price_per_token": Decimal("0.000010"),
    },
]


class MappingResult:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def all(self) -> list[dict[str, Any]]:
        return list(self._rows)


class QueryResult:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def mappings(self) -> MappingResult:
        return MappingResult(self._rows)


class FakeModelRegistrySession:
    def __init__(self, models: list[dict[str, Any]]) -> None:
        self._models = models

    def execute(self, query: Any, params: dict[str, Any] | None = None) -> QueryResult:
        q = " ".join(str(query).lower().split())
        if "from model_policy_registry" in q:
            # Return fixture rows in the order provided; ordering is tested separately.
            return QueryResult(list(self._models))
        raise AssertionError(f"Unexpected SQL in model registry test: {query}")

    def __enter__(self) -> "FakeModelRegistrySession":
        return self

    def __exit__(self, *args: Any) -> None:
        pass


def configure_env(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://localhost:5432/modelgovernor_test")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("SIDECAR_INTERNAL_TOKENS", "test-token")
    get_settings.cache_clear()


def bind_registry_session(monkeypatch, models: list[dict[str, Any]]) -> None:
    session = FakeModelRegistrySession(models)

    @contextmanager
    def _fake_get_db_session():
        yield session

    monkeypatch.setattr("app.routes_reconcile.get_db_session", _fake_get_db_session)


# ── Tests ────────────────────────────────────────────────────────────────────


def test_list_model_policy_counts(monkeypatch) -> None:
    """Response summary counts reflect total, enabled, and per-tier breakdowns."""
    configure_env(monkeypatch)
    bind_registry_session(monkeypatch, FIXTURE_MODELS)

    response = list_model_policy()

    assert response.total_count == 7
    assert response.enabled_count == 6  # legacy-model is disabled
    assert response.frontier_count == 2
    assert response.standard_count == 2
    assert response.budget_count == 3  # gpt-4o-mini, deepseek-chat, legacy-model


def test_list_model_policy_entries_populated(monkeypatch) -> None:
    """All fixture models are represented in the response models list."""
    configure_env(monkeypatch)
    bind_registry_session(monkeypatch, FIXTURE_MODELS)

    response = list_model_policy()

    assert len(response.models) == len(FIXTURE_MODELS)
    names = {m.model_name for m in response.models}
    assert names == {m["model_name"] for m in FIXTURE_MODELS}


def test_list_model_policy_tier_values_valid(monkeypatch) -> None:
    """Every model entry carries one of the three permitted governance tiers."""
    configure_env(monkeypatch)
    bind_registry_session(monkeypatch, FIXTURE_MODELS)

    response = list_model_policy()

    for entry in response.models:
        assert entry.governance_tier in VALID_TIERS, (
            f"{entry.model_name} has unexpected tier '{entry.governance_tier}'"
        )


def test_frontier_tier_trace_ceiling(monkeypatch) -> None:
    """FRONTIER models carry the elevated per-trace ceiling of 150.000000."""
    configure_env(monkeypatch)
    bind_registry_session(monkeypatch, FIXTURE_MODELS)

    response = list_model_policy()

    for entry in response.models:
        if entry.governance_tier == "FRONTIER":
            assert entry.max_cost_per_trace == Decimal("150.000000"), (
                f"{entry.model_name} FRONTIER max_cost_per_trace should be 150.000000"
            )


def test_budget_tier_trace_ceiling(monkeypatch) -> None:
    """BUDGET models carry the conservative per-trace ceiling of 25.000000."""
    configure_env(monkeypatch)
    bind_registry_session(monkeypatch, FIXTURE_MODELS)

    response = list_model_policy()

    for entry in response.models:
        if entry.governance_tier == "BUDGET" and entry.enabled:
            assert entry.max_cost_per_trace == Decimal("25.000000"), (
                f"{entry.model_name} BUDGET max_cost_per_trace should be 25.000000"
            )


def test_reasoning_models_stream_restricted(monkeypatch) -> None:
    """Reasoning models (o3, o4-mini, deepseek-reasoner) have stream_allowed=False."""
    reasoning_models = {"o3", "o4-mini", "deepseek-reasoner"}
    reasoning_fixtures = [
        m for m in FIXTURE_MODELS if m["model_name"] in reasoning_models
    ]
    configure_env(monkeypatch)
    bind_registry_session(monkeypatch, reasoning_fixtures)

    response = list_model_policy()

    for entry in response.models:
        if entry.model_name in reasoning_models:
            assert entry.stream_allowed is False, (
                f"{entry.model_name} is a reasoning model and must have stream_allowed=False"
            )


def test_frontier_cost_ceiling_above_standard(monkeypatch) -> None:
    """FRONTIER max_cost_per_request must exceed STANDARD, and STANDARD must exceed BUDGET."""
    configure_env(monkeypatch)
    bind_registry_session(monkeypatch, FIXTURE_MODELS)

    response = list_model_policy()

    enabled = [m for m in response.models if m.enabled]
    frontier_max = max(m.max_cost_per_request for m in enabled if m.governance_tier == "FRONTIER")
    standard_max = max(m.max_cost_per_request for m in enabled if m.governance_tier == "STANDARD")
    budget_max = max(m.max_cost_per_request for m in enabled if m.governance_tier == "BUDGET")

    assert frontier_max > standard_max, "FRONTIER max_cost_per_request must exceed STANDARD"
    assert standard_max > budget_max, "STANDARD max_cost_per_request must exceed BUDGET"


def test_list_model_policy_empty_registry(monkeypatch) -> None:
    """An empty registry returns a valid response with zero counts."""
    configure_env(monkeypatch)
    bind_registry_session(monkeypatch, [])

    response = list_model_policy()

    assert response.total_count == 0
    assert response.enabled_count == 0
    assert response.budget_count == 0
    assert response.standard_count == 0
    assert response.frontier_count == 0
    assert response.models == []
