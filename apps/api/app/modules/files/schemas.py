from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RepositoryFileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    repository_id: UUID
    path: str
    filename: str
    extension: str | None
    language: str | None
    size_bytes: int
    is_binary: bool
    discovered_at: datetime
    created_at: datetime
    updated_at: datetime


class RepositoryFileListResponse(BaseModel):
    files: list[RepositoryFileRead]
    page: int
    page_size: int
    has_next_page: bool


class RepositoryStatsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    repository_id: UUID
    total_files: int
    source_files: int
    binary_files: int
    total_size_bytes: int
    languages: dict[str, int]
    last_scan_at: datetime | None
