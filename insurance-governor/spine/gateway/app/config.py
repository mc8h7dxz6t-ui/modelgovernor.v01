from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ig_sidecar_url: str = "http://localhost:8101"
    ig_internal_token: str = "dev-ig-spine-token-change-me"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
