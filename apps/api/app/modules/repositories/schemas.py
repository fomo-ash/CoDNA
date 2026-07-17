from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.repositories.enums import RepositoryStatus


class RepositoryBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    full_name: str = Field(min_length=1, max_length=255)
    default_branch: str | None = Field(default=None, max_length=255)
    clone_url: str | None = Field(default=None, max_length=2048)
    visibility: str = Field(min_length=1, max_length=32)
    status: RepositoryStatus


class RepositoryImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    github_id: str | None = Field(default=None, min_length=1, max_length=255)
    full_name: str | None = Field(default=None, min_length=3, max_length=255)

    @model_validator(mode="after")
    def validate_single_identifier(self) -> "RepositoryImportRequest":
        if (self.github_id is None) == (self.full_name is None):
            raise ValueError("Provide exactly one of github_id or full_name.")
        return self


class RepositoryRead(RepositoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID | None
    github_id: str | None
    last_indexed_at: datetime | None
    created_at: datetime
    updated_at: datetime
