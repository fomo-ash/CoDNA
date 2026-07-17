from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str
    app_version: str
    app_env: str
    log_level: str
    database_url: str
    redis_url: str
    openai_api_key: str | None = None
    github_client_id: str | None = None
    github_client_secret: str | None = None
    jwt_secret: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
