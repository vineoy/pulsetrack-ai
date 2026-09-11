from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration comes from environment variables (12-factor style).

    Field names map to env vars case-insensitively: database_url <- DATABASE_URL.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "PulseTrack AI"
    environment: str = "local"  # local | production
    api_v1_prefix: str = "/api/v1"
    debug: bool = True

    database_url: str = "postgresql+asyncpg://pulse:pulse@localhost:5432/pulsetrack"
    redis_url: str = "redis://localhost:6379/0"

    # Declared now so .env.example matches config; used from Phase 1 onwards.
    jwt_secret: str = "dev-only-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    gemini_api_key: str = ""
    resend_api_key: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
