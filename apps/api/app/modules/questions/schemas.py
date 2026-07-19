from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class RepositoryQuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)


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
