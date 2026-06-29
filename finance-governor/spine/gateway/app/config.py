from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    fg_sidecar_url: str = "http://localhost:8091"
    fg_internal_token: str = "dev-fg-spine-token-change-me"

    oidc_enabled: bool = False
    oidc_issuer_url: str = ""
    oidc_jwks_url: str = ""
    oidc_audience: str = ""
    oidc_algorithms: str = "RS256"
    oidc_commit_roles: str = "fg-commit,financial-admin"
    oidc_allow_internal_token_fallback: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    def oidc_algorithms_list(self) -> list[str]:
        return [a.strip() for a in self.oidc_algorithms.split(",") if a.strip()]

    def oidc_commit_roles_list(self) -> list[str]:
        return [r.strip().lower() for r in self.oidc_commit_roles.split(",") if r.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
