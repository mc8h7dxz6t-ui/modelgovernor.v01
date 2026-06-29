"""Finance Governor Platform SDK — plug-and-play spine integration."""
from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Generator, Iterator

from fastapi import FastAPI

from .facet_schemas import FacetValidationError, validate_facets
from .platform_metrics import get_platform_counters, register_platform_counters
from .platform_observability import mount_platform_observability
from .spine_adapter import CommitOutcome, HorizonStranded, SpineAdapter, SurpriseCommitBlocked

logger = logging.getLogger(__name__)


@dataclass
class PlatformConfig:
    """Declarative platform contract for plug-and-play integration."""

    name: str
    display_name: str
    default_risk_tier: str = "high"
    default_policy_id: str | None = None
    facet_schema: dict[str, Any] = field(default_factory=dict)
    invariant_counters: tuple[str, ...] = ()
    base_url: str | None = None


def create_platform_app(
    config: PlatformConfig,
    *,
    ready_check=None,
    extra_health=None,
) -> FastAPI:
    """Bootstrap a platform FastAPI app with observability and counter registration."""
    app = FastAPI(title=f"financegovernor-{config.name}", version="0.4.0")
    if config.invariant_counters:
        register_platform_counters(config.name, config.invariant_counters)
    mount_platform_observability(
        app,
        platform=config.name,
        ready_check=ready_check,
        extra_health=extra_health,
    )
    app.state.platform_config = config
    return app


def spine_adapter_for(config: PlatformConfig) -> SpineAdapter:
    return SpineAdapter(platform=config.name)


@dataclass
class GovernedContext:
    operation_id: str
    crystal_id: str
    facets: dict[str, Any]
    adapter: SpineAdapter


@contextmanager
def governed_operation(
    adapter: SpineAdapter,
    operation_id: str,
    facets: dict[str, Any],
    *,
    risk_tier: str = "high",
    policy_id: str | None = None,
    reserved_exposure: str = "0",
    account_id: str = "desk-default",
    validate: bool = True,
) -> Generator[GovernedContext, None, None]:
    """
    Institutional++ lifecycle: crystallize → act → commit or strand on failure.

    Usage:
        with governed_operation(adapter, op_id, facets) as ctx:
            ... domain logic ...
            adapter.commit(CommitOutcome(...))
    """
    if validate:
        validate_facets(adapter.platform, facets)
    crystal = adapter.crystallize(
        operation_id,
        risk_tier,
        facets,
        account_id=account_id,
        policy_id=policy_id,
        reserved_exposure=reserved_exposure,
    )
    ctx = GovernedContext(
        operation_id=operation_id,
        crystal_id=crystal.crystal_id,
        facets=facets,
        adapter=adapter,
    )
    try:
        yield ctx
    except HorizonStranded:
        raise
    except Exception as exc:
        logger.warning("governed_operation failed operation=%s: %s", operation_id, exc)
        try:
            adapter.strand(crystal.crystal_id, reason=str(exc))
        except Exception as strand_exc:
            logger.warning("strand after failure failed operation=%s: %s", operation_id, strand_exc)
        raise


def spine_enabled() -> bool:
    return os.environ.get("FG_SPINE_ENABLED", "false").lower() == "true"


def increment_invariant(platform: str, counter: str, delta: int = 1) -> None:
    get_platform_counters(platform).increment(counter, delta)


__all__ = [
    "CommitOutcome",
    "FacetValidationError",
    "GovernedContext",
    "HorizonStranded",
    "PlatformConfig",
    "SurpriseCommitBlocked",
    "create_platform_app",
    "governed_operation",
    "increment_invariant",
    "spine_adapter_for",
    "spine_enabled",
    "validate_facets",
]
