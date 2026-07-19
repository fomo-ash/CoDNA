from __future__ import annotations

from functools import lru_cache

from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str
    app_version: str
    app_env: str
    log_level: str
    database_url: str
    redis_url: str
    repository_workspace_path: str = "/tmp/codna/repositories"
    repository_file_max_bytes: int = 10 * 1024 * 1024
    repository_file_discovery_limit: int = 5000
    openai_api_key: str | None = None
    google_api_key: str | None = None
    embedding_provider: Literal["openai", "google"] = "google"
    embedding_model: str = "gemini-embedding-001"
    embedding_dimensions: int = 1536
    embedding_batch_size: int = 64

    @field_validator("embedding_dimensions")
    @classmethod
    def validate_embedding_dimensions(cls, value: int) -> int:
        if value != 1536:
            raise ValueError("EMBEDDING_DIMENSIONS must be 1536 for the configured pgvector index.")
        return value
    github_client_id: str | None = None
    github_client_secret: str | None = None
    jwt_secret: str | None = None
    github_callback_url: str | None = None
    github_authorize_url: str | None = None
    github_token_url: str | None = None
    github_user_url: str | None = None
    github_api_url: str | None = None
    github_repositories_url: str | None = None
    github_scope: str | None = None
    frontend_url: str | None = None
    jwt_algorithm: str | None = None
    jwt_expire_minutes: int | None = None
    oauth_state_expire_minutes: int | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
