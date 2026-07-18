from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class RepositoryChunkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    repository_id: UUID
    repository_file_id: UUID | None
    path: str
    chunk_type: str
    source_type: str
    title: str
    language: str | None
    content: str
    start_line: int | None
    end_line: int | None
    metadata: dict = Field(validation_alias=AliasChoices("metadata_", "metadata"))
    created_at: datetime
    updated_at: datetime


class RepositoryChunkListResponse(BaseModel):
    chunks: list[RepositoryChunkRead]
    page: int
    page_size: int
    has_next_page: bool
