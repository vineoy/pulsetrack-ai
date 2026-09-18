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

    # Port 5433 on the host: a local PostgreSQL service already owns 5432 on this machine.
    database_url: str = "postgresql+asyncpg://pulse:pulse@localhost:5433/pulsetrack"
    redis_url: str = "redis://localhost:6379/0"

    # Declared now so .env.example matches config; used from Phase 1 onwards.
    jwt_secret: str = "dev-only-change-me-0123456789abcdef-0123456789abcdef"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    gemini_api_key: str = ""
    # gemini-2.0-flash is retired; 3.5-flash-lite is the cheapest/fastest
    # free-tier text model (verified 2026-09-17). Overridable per environment.
    gemini_model: str = "gemini-3.5-flash-lite"
    telegram_bot_token: str = ""
    telegram_bot_username: str = ""
    telegram_escalation_delay_min: int = 10
    telegram_link_expire_min: int = 15


@lru_cache
def get_settings() -> Settings:
    return Settings()
