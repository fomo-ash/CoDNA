from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RepositoryBase(BaseModel):
    name: str
    full_name: str
    default_branch: str | None = None
    clone_url: str | None = None
    visibility: str
    status: str


class RepositoryCreate(RepositoryBase):
    github_id: str | None = None
    owner_id: UUID | None = None


class RepositoryRead(RepositoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID | None
    github_id: str | None
    last_indexed_at: datetime | None
    created_at: datetime
    updated_at: datetime
