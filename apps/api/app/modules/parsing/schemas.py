from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RepositoryFileParseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    repository_id: UUID
    repository_file_id: UUID
    path: str
    language: str | None
    parser: str | None
    status: str
    root_node_type: str | None
    has_error: bool
    error_count: int
    symbol_count: int
    import_count: int
    symbols: list[dict]
    imports: list[dict]
    parsed_at: datetime | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class RepositoryFileParseListResponse(BaseModel):
    parse_results: list[RepositoryFileParseRead]
    page: int
    page_size: int
    has_next_page: bool
