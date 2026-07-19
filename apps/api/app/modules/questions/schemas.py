from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class RepositoryQuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    impact_path: str | None = Field(default=None, min_length=1, max_length=2048)
    impact_depth: int = Field(default=2, ge=1, le=3)


class RepositoryImpactExplanationRequest(BaseModel):
    path: str = Field(min_length=1, max_length=2048)
    depth: int = Field(default=2, ge=1, le=3)
    question: str | None = Field(default=None, min_length=1, max_length=1000)


class RepositoryAnswerCitation(BaseModel):
    index: int
    chunk_id: UUID
    path: str
    start_line: int | None
    end_line: int | None
    title: str


class RepositoryQuestionResponse(BaseModel):
    repository_id: UUID
    question: str
    answer: str
    citations: list[RepositoryAnswerCitation]
    vector_search_used: bool
    cached: bool = False
