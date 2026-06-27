from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    cg_sidecar_url: str = "http://localhost:8101"
    cg_internal_token: str = "dev-cg-spine-token-change-me"
    oidc_enabled: bool = False
    oidc_issuer_url: str | None = None
    oidc_audience: str | None = None
    oidc_jwks_url: str | None = None
    oidc_algorithms: str = "RS256"
    oidc_allow_internal_token_fallback: bool = True
    oidc_commit_roles: str = "commit,security-admin,cybersecuritygovernor-commit"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    def oidc_algorithms_list(self) -> list[str]:
        return [part.strip() for part in self.oidc_algorithms.split(",") if part.strip()]

    def oidc_commit_roles_list(self) -> list[str]:
        return [part.strip().lower() for part in self.oidc_commit_roles.split(",") if part.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
