from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    db_pool_size: int = 2
    db_max_overflow: int = 1
    db_pool_timeout_seconds: int = 5
    db_pool_recycle_seconds: int = 1800
    sweep_interval_seconds: int = 30
    health_port: int = 8082
    sweep_batch_size: int = 100

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
