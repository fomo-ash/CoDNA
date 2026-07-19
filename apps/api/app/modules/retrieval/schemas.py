from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.chunks.schemas import RepositoryChunkRead


class RepositorySearchResult(BaseModel):
    chunk: RepositoryChunkRead
    score: float
    lexical_score: float = 0
    vector_score: float | None = None


class RepositorySearchResponse(BaseModel):
    repository_id: UUID
    query: str
    results: list[RepositorySearchResult]
    vector_search_used: bool


class RepositorySearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    source_type: str | None = Field(default=None, max_length=64)
    chunk_type: str | None = Field(default=None, max_length=64)
    limit: int = Field(default=20, ge=1, le=100)
