from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5434/cybersecuritygovernor"
    redis_url: str = "redis://localhost:6381/0"
    reconciler_interval_seconds: int = 5
    reconciler_health_port: int = 8122
    cg_internal_tokens: str = "dev-cg-spine-token-change-me"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
