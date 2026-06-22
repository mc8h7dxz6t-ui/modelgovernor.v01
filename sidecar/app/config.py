from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    redis_url: str
    sidecar_internal_tokens: str
    reserve_ttl_seconds: int = 300
    app_env: str = "development"
    # Governance fail posture when the backing store is unavailable.
    # "fail_closed" (default) returns HTTP 503 and prevents dispatch.
    # Reserve-before-dispatch is a non-negotiable invariant so fail_open
    # is intentionally not supported on governance-critical paths.
    degraded_mode: Literal["fail_closed"] = "fail_closed"
    metrics_enabled: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
