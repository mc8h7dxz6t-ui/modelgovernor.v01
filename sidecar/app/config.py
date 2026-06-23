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
    db_pool_size: int = 5
    db_max_overflow: int = 2
    db_pool_timeout_seconds: int = 5
    db_pool_recycle_seconds: int = 1800
    app_env: str = "development"
    orchestration_runtime_mode: str = "coexisting"
    orchestration_shadow_mode: bool = True
    orchestration_cache_ttl_seconds: int = 900

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
