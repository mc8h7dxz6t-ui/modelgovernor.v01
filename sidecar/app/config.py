from functools import lru_cache
from decimal import Decimal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    redis_url: str
    sidecar_internal_tokens: str
    reserve_ttl_seconds: int = 300
    default_trace_cap_amount: Decimal = Decimal("25.000000")
    drift_absolute_tolerance: Decimal = Decimal("0.500000")
    drift_ratio_tolerance: Decimal = Decimal("0.050000")
    default_run_budget_amount: Decimal = Decimal("25.000000")
    default_session_budget_amount: Decimal = Decimal("250.000000")
    default_user_budget_amount: Decimal = Decimal("500.000000")
    default_tenant_budget_amount: Decimal = Decimal("5000.000000")
    manual_approval_cost_threshold: Decimal = Decimal("2.000000")
    max_loop_repeats: int = 3
    db_pool_size: int = 5
    db_max_overflow: int = 2
    db_pool_timeout_seconds: int = 5
    db_pool_recycle_seconds: int = 1800
    app_env: str = "development"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
